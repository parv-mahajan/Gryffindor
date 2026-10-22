"""Show which clear reports end up flagged for review, and why.

Ground truth comes from the seeded label, not from the stored flag, so the
output answers the real question: "does the model flag a report it should
have been able to classify?".

Usage:  python scripts/inspect_flags.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import AuditLog, Complaint  # noqa: E402
from app.services import classifier  # noqa: E402


def seeded_labels(db) -> dict[int, dict]:
    labels: dict[int, dict] = {}
    rows = db.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "complaint", AuditLog.action == "ai_classification"
        )
    ).scalars()
    for row in rows:
        if row.old_value and "seed_label" in row.old_value:
            labels[row.entity_id] = row.old_value
    return labels


def main() -> None:
    with SessionLocal() as db:
        complaints = db.execute(select(Complaint)).scalars().all()
        labels = seeded_labels(db)

    flagged = 0
    for complaint in complaints:
        truth = labels.get(complaint.id, {})
        if truth.get("vague"):
            continue  # deliberately vague, expected to be flagged
        result = classifier.classify(complaint.description)
        if not result["needs_review"]:
            continue
        flagged += 1
        e = result["explanation"]
        if flagged <= 15:
            print(
                f"conf={result['confidence']:.3f} cat={result['category']:<11s} "
                f"gap={e['top1_top2_gap']:.3f} kw={e['matched_keywords'][:2]} "
                f"sim={e['prototype_similarity']:.3f} abs={e['absolute_gate']:.2f} "
                f"spec={e['specificity']:.2f} words={e['content_words']} "
                f"| {complaint.description[:64]}"
            )
            print(f"    reason: {e['review_reason']}")
    print(f"total clear reports flagged: {flagged}")


if __name__ == "__main__":
    main()
