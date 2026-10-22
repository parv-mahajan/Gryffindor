"""Acceptance checks for the current build phase.

Usage:  python scripts/verify.py
Exits non-zero when a check fails.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.db import engine  # noqa: E402
from app import settings  # noqa: E402

API = "http://127.0.0.1:8000"
results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    results.append((ok, f"{label}{(' - ' + detail) if detail else ''}"))


def post_auth(path: str, payload: dict, token: str | None = None):
    """POST with an optional bearer token."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode())


def get_auth(path: str, token: str | None = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API}{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def patch(path: str, payload: dict, token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="PATCH",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode())


def get(path: str, token: str | None = None):
    return get_auth(path, token)


def post(path: str, payload: dict, token: str | None = None):
    return post_auth(path, payload, token)


def main() -> None:
    with engine.begin() as conn:
        version = conn.execute(text("SELECT postgis_version()")).scalar_one()
        check("3." in version, "PostGIS extension enabled", version)

        gist = conn.execute(
            text("SELECT indexname FROM pg_indexes "
                 "WHERE tablename='complaints' AND indexdef ILIKE '%gist%'")
        ).scalars().all()
        check(bool(gist), "GiST index on complaints.location", ", ".join(gist))

        total = conn.execute(text("SELECT count(*) FROM complaints")).scalar_one()
        check(
            total >= settings.SEED_COMPLAINTS,
            "seeded corpus present",
            f"{total} complaints",
        )

        incidents = conn.execute(text("SELECT count(*) FROM incidents")).scalar_one()
        check(
            incidents < total and incidents >= total * 0.5,
            "duplicates share one parent incident",
            f"{incidents} incidents for {total} complaints",
        )

        merged = conn.execute(
            text("SELECT count(*) FROM incidents WHERE merged_count > 0")
        ).scalar_one()
        check(merged >= 5, "incidents with merged duplicates", str(merged))

        links = conn.execute(
            text("SELECT count(*) FROM complaint_links")
        ).scalar_one()
        check(links >= 10, "duplicate / related links stored", str(links))

        accepted = conn.execute(
            text("SELECT count(*) FROM complaint_links WHERE status = 'accepted'")
        ).scalar_one()
        check(accepted >= 5, "reviewed duplicate links", str(accepted))

        by_status = dict(
            conn.execute(text("SELECT status, count(*) FROM complaints GROUP BY status")).all()
        )
        check(
            len(by_status) >= 5 and by_status.get("resolved", 0) > 0,
            "mix of lifecycle statuses",
            json.dumps(by_status),
        )

        by_category = dict(
            conn.execute(text("SELECT category_key, count(*) FROM complaints GROUP BY category_key")).all()
        )
        check(
            len(by_category) >= 5,
            "mix of categories",
            json.dumps(by_category),
        )

        review = conn.execute(
            text("SELECT count(*) FROM complaints WHERE needs_review IS TRUE")
        ).scalar_one()
        check(review >= 5, "low-confidence complaints flagged for review", str(review))

        # duplicate groups: same category, within 30 m
        pairs = conn.execute(
            text(
                """
                SELECT a.ticket_id, b.ticket_id, round(ST_Distance(a.location, b.location)::numeric, 1) AS d
                FROM complaints a JOIN complaints b
                  ON a.id < b.id
                 AND a.category_key = b.category_key
                 AND ST_DWithin(a.location, b.location, 30)
                ORDER BY d
                LIMIT 5
                """
            )
        ).all()
        group_count = conn.execute(
            text(
                """
                SELECT count(*) FROM (
                  SELECT a.id FROM complaints a JOIN complaints b
                    ON a.id < b.id AND a.category_key = b.category_key
                   AND ST_DWithin(a.location, b.location, 30)
                  GROUP BY a.id
                ) g
                """
            )
        ).scalar_one()
        check(group_count >= 10, "deliberate duplicate groups within 30 m", f"{group_count} groups")
        if pairs:
            check(True, "closest duplicate pair", f"{pairs[0][0]} / {pairs[0][1]} at {pairs[0][2]} m")

        # hotspot: repeated potholes along central avenue
        hotspot = conn.execute(
            text(
                """
                SELECT count(*) FROM complaints
                 WHERE category_key='pothole'
                   AND ST_DWithin(location, ST_SetSRID(ST_MakePoint(72.8776, 19.0752),4326)::geography, 350)
                """
            )
        ).scalar_one()
        check(hotspot >= 6, "recurring pothole hotspot on central avenue", str(hotspot))

        stored = conn.execute(
            text("SELECT ticket_id, ST_AsText(location) FROM complaints LIMIT 1")
        ).one()
        check(stored[1].startswith("POINT"), "location stored as geography point", stored[1])

        embedded = conn.execute(
            text("SELECT count(*) FROM complaints WHERE embedding IS NOT NULL")
        ).scalar_one()
        check(embedded == total, "embeddings stored for every complaint", str(embedded))

    # API checks - everything below the queue needs an admin session
    session = post_auth("/auth/login", {"username": "admin", "password": "1234"})
    check(
        session.get("role") == "admin" and bool(session.get("token")),
        "admin can sign in",
        session.get("username", ""),
    )
    admin_token = session["token"]

    try:
        post_auth("/auth/login", {"username": "admin", "password": "nope"})
        check(False, "wrong password is refused")
    except urllib.error.HTTPError as exc:
        check(exc.code == 401, "wrong password is refused", str(exc.code))

    try:
        post_auth("/auth/login", {"username": "ghost", "password": "1234"})
        check(False, "unknown user is refused")
    except urllib.error.HTTPError as exc:
        check(exc.code == 401, "unknown user is refused", str(exc.code))

    reporter = post_auth("/auth/login", {"username": "reporter", "password": "1234"})
    try:
        get_auth("/complaints?limit=5", reporter["token"])
        check(False, "reporter cannot read the admin queue")
    except urllib.error.HTTPError as exc:
        check(exc.code == 403, "reporter cannot read the admin queue", str(exc.code))

    me = get_auth("/auth/me", admin_token)
    check(me.get("username") == "admin", "session can be inspected", me.get("username", ""))

    complaints = get("/complaints?limit=200", admin_token)
    check(
        len(complaints) >= settings.SEED_COMPLAINTS,
        "GET /complaints returns the corpus",
        str(len(complaints)),
    )
    scores = [c["priority_score"] for c in complaints]
    check(scores == sorted(scores, reverse=True), "queue sorted by priority desc")

    filtered = get("/complaints?status=resolved", admin_token)
    check(
        len(filtered) > 0 and all(c["status"] == "resolved" for c in filtered),
        "status filter works",
        f"{len(filtered)} resolved",
    )

    cat_filtered = get("/complaints?category=pothole", admin_token)
    check(
        len(cat_filtered) > 0 and all(c["category_key"] == "pothole" for c in cat_filtered),
        "category filter works",
        f"{len(cat_filtered)} pothole",
    )

    ticket = complaints[0]["ticket_id"]
    ticket_status = get(f"/tickets/{ticket}")
    check(ticket_status["ticket_id"] == ticket, "public ticket lookup works", ticket)

    try:
        get("/tickets/CS-DOESNOTEXIST")
        check(False, "unknown ticket returns 404")
    except urllib.error.HTTPError as exc:
        check(exc.code == 404, "unknown ticket returns 404", str(exc.code))

    try:
        get("/complaints?limit=5")
        check(False, "dashboard data needs a session")
    except urllib.error.HTTPError as exc:
        check(exc.code == 401, "dashboard data needs a session", str(exc.code))

    # dashboard stats
    workload = get("/complaints/stats/workload", admin_token)
    check(
        len(workload) >= 5
        and all("capacity" in row and "open" in row for row in workload),
        "department workload endpoint",
        f"{len(workload)} departments",
    )

    hotspots = get("/complaints/stats/hotspots", admin_token)
    check(
        len(hotspots) >= 1 and hotspots[0]["count"] >= 3,
        "hotspot clustering endpoint",
        f"top cluster has {hotspots[0]['count']} reports" if hotspots else "none",
    )

    # workflow: a submitted complaint can be triaged, an illegal jump is refused
    submitted = get("/complaints?status=submitted&limit=1", admin_token)
    if submitted:
        target = submitted[0]
        updated = patch(
            f"/complaints/{target['id']}/status",
            {"status": "triaged", "reason": "verify"},
            admin_token,
        )
        check(updated["status"] == "triaged", "status transition works", target["ticket_id"])
    else:
        check(False, "status transition works", "no submitted complaint to move")

    resolved = get("/complaints?status=resolved&limit=1", admin_token)
    if resolved:
        try:
            patch(f"/complaints/{resolved[0]['id']}/status", {"status": "submitted"}, admin_token)
            check(False, "illegal status transition is refused")
        except urllib.error.HTTPError as exc:
            check(exc.code == 409, "illegal status transition is refused", str(exc.code))
    else:
        check(False, "illegal status transition is refused", "no resolved complaint")

    # a reporter may not drive the workflow
    try:
        patch("/complaints/1/status", {"status": "triaged"}, reporter["token"])
        check(False, "reporter cannot change status")
    except urllib.error.HTTPError as exc:
        check(exc.code == 403, "reporter cannot change status", str(exc.code))

    # review queue: a flagged complaint can be confirmed
    flagged = get("/complaints?needs_review=true&limit=1", admin_token)
    if flagged:
        item = flagged[0]
        decision = post(
            f"/complaints/{item['id']}/review",
            {
                "category_key": item["category_key"],
                "confirm": True,
                "reason": "verified by civic admin",
            },
            admin_token,
        )
        check(
            decision["needs_review"] is False,
            "review decision clears the flag",
            item["ticket_id"],
        )
    else:
        check(False, "review decision clears the flag", "review queue is empty")

    # duplicate detection: submitting a reworded report at the same spot links
    # it to the complaint it repeats
    reference = get("/complaints?category=pothole&limit=1", admin_token)[0]
    with engine.begin() as conn:
        corpus_size = conn.execute(text("SELECT count(*) FROM complaints")).scalar_one()
    body = urllib.parse.urlencode(
        {
            "description": (
                "Huge deep pothole in the middle of the road, two wheelers are "
                "skidding near this exact spot"
            ),
            "lat": reference["lat"],
            "lng": reference["lng"],
            "reporter_name": "Verification Bot",
        }
    ).encode()
    request = urllib.request.Request(
        f"{API}/complaints",
        data=body,
        headers={
            "Authorization": f"Bearer {reporter['token']}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        created = json.loads(response.read().decode())
    found = created.get("duplicates") or []
    check(bool(found), "new report is matched to an existing one", f"{len(found)} candidate(s)")
    check(
        found and found[0]["relation"] in {"duplicate", "related"},
        "duplicate candidate carries a relation",
        found[0]["relation"] if found else "none",
    )
    check(
        created["priority"]["factors"]["related_reports"] > 0,
        "related reports feed the priority score",
        str(created["priority"]["factors"]["related_reports"]),
    )
    check(
        created["complaint"]["department_key"] is not None,
        "new reports are routed to a department",
        str(created["complaint"]["department_key"]),
    )

    # clean up the probe so the corpus is left exactly as it was
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM complaint_links WHERE complaint_id = :id OR linked_complaint_id = :id"),
            {"id": created["complaint"]["id"]},
        )
        conn.execute(
            text("DELETE FROM audit_log WHERE entity_id = :id AND entity_type = 'complaint'"),
            {"id": created["complaint"]["id"]},
        )
        conn.execute(
            text("DELETE FROM incidents WHERE id = :id"),
            {"id": created["complaint"]["incident_id"]},
        )
        conn.execute(
            text("DELETE FROM complaints WHERE id = :id"), {"id": created["complaint"]["id"]}
        )
        left = conn.execute(text("SELECT count(*) FROM complaints")).scalar_one()
    check(left == corpus_size, "probe removed, corpus unchanged", f"{left} of {corpus_size}")

    print()
    failures = 0
    for ok, label in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
        failures += 0 if ok else 1
    print(f"\n{len(results) - failures}/{len(results)} checks passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
