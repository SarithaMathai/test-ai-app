"""Extended evaluation pipeline — detailed accuracy metrics by signal, department, and LLM impact."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from plm_tcin_mapper_api.database.models import (
    ConfidenceTier,
    DepartmentMetrics,
    ExtendedEvalRun,
    LLMImpactMetrics,
    SignalAccuracy,
)

_MAPPINGS_COL = "mappings"
_FEEDBACK_COL = "feedback"
_EXTENDED_EVAL_COL = "extended_eval_runs"


def run_extended_eval(db: Any, persist: bool = True) -> ExtendedEvalRun:
    """Compute detailed evaluation metrics from mappings and feedback."""
    mappings_col = db[_MAPPINGS_COL]
    feedback_col = db[_FEEDBACK_COL]

    total = mappings_col.count_documents({})
    if total == 0:
        run = ExtendedEvalRun(
            total_mappings=0,
            guardrail_alerts=["No mappings found in database."],
        )
        if persist:
            db[_EXTENDED_EVAL_COL].insert_one(run.model_dump(by_alias=True))
        return run

    mappings = list(mappings_col.find({}))
    feedback_by_mapping = _build_feedback_index(feedback_col)

    by_status = _count_by_status(mappings)
    by_tier = _count_by_tier(mappings)

    per_signal_accuracy = _compute_per_signal_accuracy(mappings, feedback_by_mapping)
    per_department_metrics = _compute_per_department_metrics(mappings, feedback_by_mapping)
    llm_impact = _compute_llm_impact(mappings, feedback_by_mapping)
    confidence_calibration_error = _compute_calibration_error(mappings, feedback_by_mapping)

    avg_color_confidence = _compute_avg_confidence(mappings)
    correction_rate = _compute_correction_rate(mappings, feedback_by_mapping)
    n_high = by_tier.get(ConfidenceTier.HIGH, 0)
    n_good = by_tier.get(ConfidenceTier.GOOD, 0)
    n_fair = by_tier.get(ConfidenceTier.FAIR, 0)
    n_low = by_tier.get(ConfidenceTier.LOW, 0)

    def pct(count: int) -> float:
        return round(count / total, 4) if total else 0.0

    high_confidence_corrections = _count_high_confidence_corrections(mappings, feedback_by_mapping)
    low_confidence_corrections = _count_low_confidence_corrections(mappings, feedback_by_mapping)

    high_confidence_total = n_high
    low_confidence_total = n_low

    high_confidence_correction_rate = (
        round(high_confidence_corrections / high_confidence_total, 4) if high_confidence_total > 0 else 0.0
    )
    low_confidence_correction_rate = (
        round(low_confidence_corrections / low_confidence_total, 4) if low_confidence_total > 0 else 0.0
    )

    run = ExtendedEvalRun(
        total_mappings=total,
        by_status=by_status,
        by_tier=by_tier,
        pct_high=pct(n_high),
        pct_good=pct(n_good),
        pct_fair=pct(n_fair),
        pct_low=pct(n_low),
        avg_color_confidence=avg_color_confidence,
        correction_rate=correction_rate,
        per_signal_accuracy=per_signal_accuracy,
        per_department_metrics=per_department_metrics,
        llm_impact=llm_impact,
        confidence_calibration_error=confidence_calibration_error,
        high_confidence_actual_correction_rate=high_confidence_correction_rate,
        low_confidence_actual_correction_rate=low_confidence_correction_rate,
    )

    if persist:
        db[_EXTENDED_EVAL_COL].insert_one(run.model_dump(by_alias=True))

    return run


def _build_feedback_index(feedback_col: Any) -> dict[str, Any]:
    """Build a mapping_id -> feedback record index."""
    index: dict[str, Any] = defaultdict(lambda: [])
    for feedback in feedback_col.find({}):
        mapping_id = feedback.get("mapping_id", "")
        if mapping_id:
            index[mapping_id].append(feedback)
    return index


def _count_by_status(mappings: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for mapping in mappings:
        status = str(mapping.get("status", "UNKNOWN"))
        counts[status] += 1
    return dict(counts)


def _count_by_tier(mappings: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for mapping in mappings:
        tier = str(mapping.get("confidence_tier", "UNKNOWN"))
        counts[tier] += 1
    return dict(counts)


def _compute_avg_confidence(mappings: list[Any]) -> float:
    if not mappings:
        return 0.0
    total = sum(float(m.get("color_confidence", 0.0)) for m in mappings)
    return round(total / len(mappings), 4)


def _compute_correction_rate(mappings: list[Any], feedback_by_mapping: dict[str, Any]) -> float:
    corrected = 0
    human_reviewed = 0

    for mapping in mappings:
        status = str(mapping.get("status", ""))
        if status in ("CONFIRMED", "REJECTED", "CORRECTED"):
            human_reviewed += 1
            if status == "CORRECTED":
                corrected += 1

    return round(corrected / human_reviewed, 4) if human_reviewed > 0 else 0.0


def _compute_per_signal_accuracy(
    mappings: list[Any],
    feedback_by_mapping: dict[str, Any],
) -> dict[str, SignalAccuracy]:
    """Track accuracy of each scoring signal (token_overlap, keyword_match, fuzzy)."""
    signal_stats: dict[str, dict] = defaultdict(
        lambda: {
            "occurrences": 0,
            "corrections": 0,
            "confidence_sum": 0.0,
            "by_tier": defaultdict(int),
        }
    )

    for mapping in mappings:
        reason = mapping.get("color_match_reason", "")
        if not reason:
            continue

        signal_type = _extract_signal_type(reason)
        confidence = float(mapping.get("color_confidence", 0.0))
        tier = str(mapping.get("confidence_tier", "UNKNOWN"))

        signal_stats[signal_type]["occurrences"] += 1
        signal_stats[signal_type]["confidence_sum"] += confidence
        signal_stats[signal_type]["by_tier"][tier] += 1

        mapping_id = str(mapping.get("_id", ""))
        if mapping_id in feedback_by_mapping:
            for feedback in feedback_by_mapping[mapping_id]:
                if str(feedback.get("action", "")) == "CORRECT":
                    signal_stats[signal_type]["corrections"] += 1
                    break

    result = {}
    for signal_type, stats in signal_stats.items():
        occurrences = stats["occurrences"]
        corrections = stats["corrections"]
        correction_rate = round(corrections / occurrences, 4) if occurrences > 0 else 0.0
        avg_confidence = round(stats["confidence_sum"] / occurrences, 4) if occurrences > 0 else 0.0

        result[signal_type] = SignalAccuracy(
            signal_type=signal_type,
            occurrences=occurrences,
            corrections=corrections,
            correction_rate=correction_rate,
            avg_confidence=avg_confidence,
            confidence_by_tier=dict(stats["by_tier"]),
        )

    return result


def _extract_signal_type(reason: str) -> str:
    """Extract signal type from match reason string.

    Reason format: "signal_name:details" or "exact_token:...", "stem_token:...", etc.
    """
    if not reason:
        return "unknown"

    parts = reason.split(":")
    signal = parts[0].lower()

    if signal in ("exact_token", "token_overlap", "stem_token", "stem_overlap"):
        return "token_overlap"
    elif signal == "keyword_match":
        return "keyword_match"
    elif signal in ("fuzzy", "fuzzy_fallback", "wratio"):
        return "fuzzy_match"
    else:
        return signal


def _compute_per_department_metrics(
    mappings: list[Any],
    feedback_by_mapping: dict[str, Any],
) -> list[DepartmentMetrics]:
    """Track accuracy per department."""
    dept_stats: dict[str, dict] = defaultdict(
        lambda: {
            "total": 0,
            "high_confidence": 0,
            "corrections": 0,
            "confidence_sum": 0.0,
            "by_match_round": defaultdict(int),
        }
    )

    for mapping in mappings:
        departments = mapping.get("department_ids", [])
        if not departments:
            departments = ["unknown"]

        confidence = float(mapping.get("color_confidence", 0.0))
        tier = str(mapping.get("confidence_tier", "UNKNOWN"))
        match_round = str(mapping.get("match_round", "UNKNOWN"))
        mapping_id = str(mapping.get("_id", ""))

        for dept in departments:
            stats = dept_stats[dept]
            stats["total"] += 1
            stats["confidence_sum"] += confidence
            if tier == "HIGH":
                stats["high_confidence"] += 1
            stats["by_match_round"][match_round] += 1

            if mapping_id in feedback_by_mapping:
                for feedback in feedback_by_mapping[mapping_id]:
                    if str(feedback.get("action", "")) == "CORRECT":
                        stats["corrections"] += 1
                        break

    metrics = []
    for dept, stats in sorted(dept_stats.items()):
        total = stats["total"]
        corrections = stats["corrections"]
        pct_high = round(stats["high_confidence"] / total, 4) if total > 0 else 0.0
        correction_rate = round(corrections / total, 4) if total > 0 else 0.0
        avg_confidence = round(stats["confidence_sum"] / total, 4) if total > 0 else 0.0

        metrics.append(
            DepartmentMetrics(
                department=dept,
                total_mappings=total,
                pct_high_confidence=pct_high,
                correction_rate=correction_rate,
                avg_confidence=avg_confidence,
                by_match_round=dict(stats["by_match_round"]),
            )
        )

    return metrics


def _compute_llm_impact(
    mappings: list[Any],
    feedback_by_mapping: dict[str, Any],
) -> LLMImpactMetrics | None:
    """Track LLM assist impact vs deterministic matching."""
    llm_calls = 0
    llm_corrected = 0
    llm_confidence_sum = 0.0
    deterministic_corrected = 0
    deterministic_confidence_sum = 0.0
    deterministic_total = 0

    for mapping in mappings:
        match_round = str(mapping.get("match_round", ""))
        confidence = float(mapping.get("color_confidence", 0.0))
        mapping_id = str(mapping.get("_id", ""))

        is_corrected = False
        if mapping_id in feedback_by_mapping:
            for feedback in feedback_by_mapping[mapping_id]:
                if str(feedback.get("action", "")) == "CORRECT":
                    is_corrected = True
                    break

        if match_round == "LLM":
            llm_calls += 1
            llm_confidence_sum += confidence
            if is_corrected:
                llm_corrected += 1
        else:
            deterministic_total += 1
            deterministic_confidence_sum += confidence
            if is_corrected:
                deterministic_corrected += 1

    if llm_calls == 0:
        return None

    llm_correction_rate = round(llm_corrected / llm_calls, 4) if llm_calls > 0 else 0.0
    deterministic_correction_rate = (
        round(deterministic_corrected / deterministic_total, 4) if deterministic_total > 0 else 0.0
    )

    improvement = round(
        deterministic_correction_rate - llm_correction_rate,
        4,
    )

    return LLMImpactMetrics(
        total_llm_calls=llm_calls,
        llm_corrected=llm_corrected,
        llm_correction_rate=llm_correction_rate,
        llm_avg_confidence=round(llm_confidence_sum / llm_calls, 4) if llm_calls > 0 else 0.0,
        deterministic_corrected=deterministic_corrected,
        deterministic_correction_rate=deterministic_correction_rate,
        llm_vs_deterministic_improvement=improvement,
    )


def _compute_calibration_error(
    mappings: list[Any],
    feedback_by_mapping: dict[str, Any],
) -> float:
    """Compute expected calibration error (ECE) for confidence scores.

    ECE measures how well confidence aligns with actual accuracy.
    Groups by confidence bins and compares predicted vs actual correction rate.
    """
    bins: dict[int, dict] = {i: {"confidence_sum": 0.0, "count": 0, "corrections": 0} for i in range(10)}

    for mapping in mappings:
        confidence = float(mapping.get("color_confidence", 0.0))
        bin_idx = min(int(confidence * 10), 9)
        mapping_id = str(mapping.get("_id", ""))

        bins[bin_idx]["confidence_sum"] += confidence
        bins[bin_idx]["count"] += 1

        if mapping_id in feedback_by_mapping:
            for feedback in feedback_by_mapping[mapping_id]:
                if str(feedback.get("action", "")) == "CORRECT":
                    bins[bin_idx]["corrections"] += 1
                    break

    total_count = sum(bin_data["count"] for bin_data in bins.values())
    if total_count == 0:
        return 0.0

    ece = 0.0
    for bin_data in bins.values():
        if bin_data["count"] == 0:
            continue

        predicted_accuracy = bin_data["confidence_sum"] / bin_data["count"]
        actual_accuracy = 1.0 - (bin_data["corrections"] / bin_data["count"])
        bin_weight = bin_data["count"] / total_count

        ece += bin_weight * abs(predicted_accuracy - actual_accuracy)

    return round(ece, 4)


def _count_high_confidence_corrections(
    mappings: list[Any],
    feedback_by_mapping: dict[str, Any],
) -> int:
    """Count how many HIGH confidence mappings were corrected."""
    count = 0
    for mapping in mappings:
        tier = str(mapping.get("confidence_tier", ""))
        if tier == "HIGH":
            mapping_id = str(mapping.get("_id", ""))
            if mapping_id in feedback_by_mapping:
                for feedback in feedback_by_mapping[mapping_id]:
                    if str(feedback.get("action", "")) == "CORRECT":
                        count += 1
                        break
    return count


def _count_low_confidence_corrections(
    mappings: list[Any],
    feedback_by_mapping: dict[str, Any],
) -> int:
    """Count how many LOW confidence mappings were corrected."""
    count = 0
    for mapping in mappings:
        tier = str(mapping.get("confidence_tier", ""))
        if tier == "LOW":
            mapping_id = str(mapping.get("_id", ""))
            if mapping_id in feedback_by_mapping:
                for feedback in feedback_by_mapping[mapping_id]:
                    if str(feedback.get("action", "")) == "CORRECT":
                        count += 1
                        break
    return count
