"""Evaluation pipeline — computes accuracy metrics and guardrail alerts."""

from __future__ import annotations

from typing import Any

from plm_tcin_mapper_api.database.models import ConfidenceTier, EvalRun, MappingStatus

_MAPPINGS_COL = "mappings"
_EVAL_COL = "eval_runs"


def run_eval(db: Any, cfg: Any, persist: bool = True) -> EvalRun:
    """Compute a full evaluation snapshot from the mappings collection."""
    mappings_col = db[_MAPPINGS_COL]
    eval_col = db[_EVAL_COL]

    total = mappings_col.count_documents({})
    if total == 0:
        run = EvalRun(total_mappings=0, guardrail_alerts=["No mappings found in database."])
        if persist:
            eval_col.insert_one(run.model_dump(by_alias=True))
        return run

    by_status: dict[str, int] = {
        doc["_id"]: doc["count"]
        for doc in mappings_col.aggregate([{"$group": {"_id": "$status", "count": {"$sum": 1}}}])
        if doc["_id"]
    }

    by_tier: dict[str, int] = {
        doc["_id"]: doc["count"]
        for doc in mappings_col.aggregate([{"$group": {"_id": "$confidence_tier", "count": {"$sum": 1}}}])
        if doc["_id"]
    }

    avg_docs = list(mappings_col.aggregate([{"$group": {"_id": None, "avg": {"$avg": "$color_confidence"}}}]))
    avg_color_confidence = round(avg_docs[0]["avg"], 4) if avg_docs else 0.0

    def pct(count: int) -> float:
        return round(count / total, 4) if total else 0.0

    n_high = by_tier.get(ConfidenceTier.HIGH, 0)
    n_good = by_tier.get(ConfidenceTier.GOOD, 0)
    n_fair = by_tier.get(ConfidenceTier.FAIR, 0)
    n_low = by_tier.get(ConfidenceTier.LOW, 0)
    n_confirmed = by_status.get(MappingStatus.CONFIRMED, 0)
    n_rejected = by_status.get(MappingStatus.REJECTED, 0)
    n_corrected = by_status.get(MappingStatus.CORRECTED, 0)

    human_reviewed = n_confirmed + n_rejected + n_corrected
    correction_rate = round(n_corrected / human_reviewed, 4) if human_reviewed else 0.0

    eval_cfg = cfg.eval
    alerts: list[str] = []

    if pct(n_high) < eval_cfg.min_high_confidence_pct:
        alerts.append(
            f"LOW HIGH-CONFIDENCE RATE: {pct(n_high):.1%} (threshold: {eval_cfg.min_high_confidence_pct:.0%})"
        )

    if pct(n_low) > eval_cfg.max_low_confidence_pct:
        alerts.append(f"HIGH LOW-CONFIDENCE RATE: {pct(n_low):.1%} (threshold: {eval_cfg.max_low_confidence_pct:.0%})")

    needs_review_count = by_status.get(MappingStatus.NEEDS_REVIEW, 0)
    if needs_review_count > eval_cfg.review_queue_backlog_limit:
        alerts.append(f"REVIEW QUEUE BACKLOG: {needs_review_count:,} mappings awaiting human review.")

    if avg_color_confidence < eval_cfg.min_avg_confidence:
        alerts.append(f"LOW AVERAGE CONFIDENCE: {avg_color_confidence:.3f}")

    run = EvalRun(
        total_mappings=total,
        by_status=by_status,
        by_tier=by_tier,
        pct_high=pct(n_high),
        pct_good=pct(n_good),
        pct_fair=pct(n_fair),
        pct_low=pct(n_low),
        pct_confirmed=pct(n_confirmed),
        pct_rejected=pct(n_rejected),
        correction_rate=correction_rate,
        avg_color_confidence=avg_color_confidence,
        guardrail_alerts=alerts,
    )

    if persist:
        eval_col.insert_one(run.model_dump(by_alias=True))

    return run
