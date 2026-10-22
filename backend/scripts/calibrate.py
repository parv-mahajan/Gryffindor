"""Calibration helper: run the classifier over the seeded corpus.

The seeded label is the ground truth: the eight deliberately vague reports are
seeded as "other", everything else has a concrete category. The script prints
the confidence distribution for both groups plus the agreement rate, so the
softmax temperature and the review thresholds can be tuned.

Usage:  python scripts/calibrate.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import AuditLog, Complaint  # noqa: E402
from app.services import classifier  # noqa: E402


def seeded_labels(db) -> dict[int, dict]:
    """Ground truth labels written by the seed script."""
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

    clear, vague = [], []
    agree = 0
    for complaint in complaints:
        result = classifier.classify(complaint.description)
        truth = labels.get(complaint.id, {})
        target = truth.get("seed_label", complaint.category_key)
        if truth.get("vague"):
            vague.append((complaint.description, result))
        else:
            clear.append((complaint.description, result, target))
            if result["category"] == target:
                agree += 1

    def summarise(rows, label):
        if not rows:
            print(f"{label}: n=0")
            return
        confs = [r[1]["confidence"] for r in rows]
        review = sum(1 for r in rows if r[1]["needs_review"])
        sims = [r[1]["explanation"]["prototype_similarity"] for r in rows]
        print(
            f"{label}: n={len(rows)} "
            f"mean_conf={sum(confs)/len(confs):.3f} "
            f"min={min(confs):.3f} max={max(confs):.3f} "
            f"flagged_review={review} "
            f"mean_sim={sum(sims)/len(sims):.3f} "
            f"min_sim={min(sims):.3f} max_sim={max(sims):.3f}"
        )

    summarise(clear, "clear reports ")
    summarise(vague, "vague reports ")

    total = len(clear) + len(vague)
    print(f"seeded category agreement: {agree}/{len(clear)} = {agree/max(1,len(clear)):.1%}")
    print(
        "overall flagged for review: "
        f"{sum(1 for r in clear + vague if r[1]['needs_review'])}/{total}"
    )

    print("\ntop predicted classes:", Counter(r[1]["category"] for r in clear + vague).most_common())
    print("\nsample vague classifications:")
    for description, result in vague[:8]:
        print(f"  {description!r} -> {result['category']} {result['confidence']:.3f} "
              f"review={result['needs_review']} gap={result['explanation']['top1_top2_gap']:.3f}")

    print("\nlowest confidence clear reports:")
    for description, result, target in sorted(clear, key=lambda r: r[1]["confidence"])[:8]:
        print(f"  {result['confidence']:.3f} pred={result['category']:12s} target={target:12s} "
              f"{description[:70]!r}")


if __name__ == "__main__":
    main()
