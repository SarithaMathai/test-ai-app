"""Shadow mode comparison — compares test batch against baseline to validate improvements."""

from __future__ import annotations

import asyncio
import math
from collections import defaultdict
from typing import Any

from ai_mongo import MongoClientManager

from plm_tcin_mapper_api.database.models import ShadowComparisonResult, ShadowMetricComparison
from plm_tcin_mapper_api.models.schemas import ShadowComparisonResponse

_MAPPINGS_COL = "mappings"
_FEEDBACK_COL = "feedback"
_SHADOW_COMPARISONS_COL = "shadow_comparisons"


class ShadowComparator:
    """Compares shadow batch results against baseline to validate configuration changes."""

    def __init__(self, mongo: MongoClientManager) -> None:
        self._mongo = mongo

    async def compare(self, baseline_batch_id: str, shadow_batch_id: str) -> ShadowComparisonResponse:
        """Compare two batches and return comprehensive comparison results."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self._compare_sync, baseline_batch_id, shadow_batch_id
        )

    def _compare_sync(self, baseline_batch_id: str, shadow_batch_id: str) -> ShadowComparisonResponse:
        db = self._mongo.get_sync_db()
        mappings_col = db[_MAPPINGS_COL]
        comparisons_col = db[_SHADOW_COMPARISONS_COL]

        baseline_mappings = list(mappings_col.find({"batch_id": baseline_batch_id}))
        shadow_mappings = list(mappings_col.find({"batch_id": shadow_batch_id}))

        if not baseline_mappings or not shadow_mappings:
            return ShadowComparisonResponse(
                status="error",
                message=f"Batch not found: baseline={len(baseline_mappings)}, shadow={len(shadow_mappings)}",
                comparison=None,
            )

        baseline_metrics = self._compute_metrics(baseline_mappings)
        shadow_metrics = self._compute_metrics(shadow_mappings)

        metric_comparisons = self._compare_metrics(baseline_metrics, shadow_metrics)

        overall_improvement = self._calculate_overall_improvement(metric_comparisons)
        p_value = self._calculate_p_value(baseline_mappings, shadow_mappings)
        is_significant = p_value < 0.05

        recommendation = self._generate_recommendation(metric_comparisons, overall_improvement, is_significant)

        result = ShadowComparisonResult(
            baseline_batch_id=baseline_batch_id,
            shadow_batch_id=shadow_batch_id,
            total_baseline_mappings=len(baseline_mappings),
            total_shadow_mappings=len(shadow_mappings),
            metric_comparisons=metric_comparisons,
            confidence_improvement=self._get_metric_improvement(metric_comparisons, "avg_confidence"),
            correction_rate_improvement=self._get_metric_improvement(metric_comparisons, "correction_rate"),
            pct_high_improvement=self._get_metric_improvement(metric_comparisons, "pct_high"),
            overall_improvement_score=overall_improvement,
            p_value=p_value,
            is_statistically_significant=is_significant,
            recommendation=recommendation,
        )

        comparisons_col.insert_one(result.model_dump(by_alias=True))

        return ShadowComparisonResponse(
            status="ok",
            message=f"Comparison complete: {len(metric_comparisons)} metrics analyzed",
            comparison={
                "baseline_batch_id": baseline_batch_id,
                "shadow_batch_id": shadow_batch_id,
                "total_baseline": len(baseline_mappings),
                "total_shadow": len(shadow_mappings),
                "metric_comparisons": [
                    {
                        "metric": m.metric,
                        "baseline": f"{m.baseline_value:.4f}",
                        "shadow": f"{m.shadow_value:.4f}",
                        "delta": f"{m.delta:+.4f}",
                        "pct_change": f"{m.pct_change:+.1%}",
                        "is_improvement": m.is_improvement,
                    }
                    for m in metric_comparisons
                ],
                "overall_improvement": f"{overall_improvement:.4f}",
                "p_value": f"{p_value:.4f}",
                "is_statistically_significant": is_significant,
                "recommendation": recommendation,
            },
        )

    def _compute_metrics(self, mappings: list[Any]) -> dict[str, float]:
        """Compute key metrics for a batch of mappings."""
        if not mappings:
            return {}

        from plm_tcin_mapper_api.database.models import ConfidenceTier, MappingStatus

        total = len(mappings)

        by_status = defaultdict(int)
        by_tier = defaultdict(int)
        confidence_sum = 0.0

        for mapping in mappings:
            status = str(mapping.get("status", ""))
            tier = str(mapping.get("confidence_tier", ""))
            confidence = float(mapping.get("color_confidence", 0.0))

            by_status[status] += 1
            by_tier[tier] += 1
            confidence_sum += confidence

        n_high = by_tier.get(str(ConfidenceTier.HIGH), 0)
        n_good = by_tier.get(str(ConfidenceTier.GOOD), 0)
        n_corrected = by_status.get(str(MappingStatus.CORRECTED), 0)
        n_confirmed = by_status.get(str(MappingStatus.CONFIRMED), 0)
        n_rejected = by_status.get(str(MappingStatus.REJECTED), 0)

        human_reviewed = n_confirmed + n_rejected + n_corrected
        correction_rate = n_corrected / human_reviewed if human_reviewed > 0 else 0.0

        return {
            "total_mappings": total,
            "avg_confidence": confidence_sum / total if total > 0 else 0.0,
            "pct_high": n_high / total if total > 0 else 0.0,
            "pct_good": n_good / total if total > 0 else 0.0,
            "correction_rate": correction_rate,
            "pct_confirmed": n_confirmed / total if total > 0 else 0.0,
            "pct_rejected": n_rejected / total if total > 0 else 0.0,
            "pct_corrected": n_corrected / total if total > 0 else 0.0,
        }

    def _compare_metrics(self, baseline: dict[str, float], shadow: dict[str, float]) -> list[ShadowMetricComparison]:
        """Compare metrics between baseline and shadow batches."""
        comparisons = []

        for metric in ["avg_confidence", "pct_high", "pct_good", "correction_rate", "pct_confirmed"]:
            baseline_val = baseline.get(metric, 0.0)
            shadow_val = shadow.get(metric, 0.0)
            delta = shadow_val - baseline_val

            if baseline_val != 0:
                pct_change = delta / baseline_val
            else:
                pct_change = 0.0

            is_improvement = (
                (delta > 0 if metric in ["avg_confidence", "pct_high", "pct_good"] else delta < 0)
                if metric != "pct_confirmed"
                else delta > 0
            )

            comparisons.append(
                ShadowMetricComparison(
                    metric=metric,
                    baseline_value=baseline_val,
                    shadow_value=shadow_val,
                    delta=delta,
                    pct_change=pct_change,
                    is_improvement=is_improvement,
                )
            )

        return comparisons

    @staticmethod
    def _calculate_overall_improvement(comparisons: list[ShadowMetricComparison]) -> float:
        """Calculate weighted overall improvement score."""
        weights = {
            "correction_rate": 0.35,
            "avg_confidence": 0.25,
            "pct_high": 0.25,
            "pct_good": 0.1,
            "pct_confirmed": 0.05,
        }

        score = 0.0
        for comp in comparisons:
            weight = weights.get(comp.metric, 0.0)
            improvement = comp.delta if comp.is_improvement else -abs(comp.delta)
            score += weight * improvement

        return score

    @staticmethod
    def _get_metric_improvement(comparisons: list[ShadowMetricComparison], metric_name: str) -> float:
        """Get improvement for a specific metric."""
        for comp in comparisons:
            if comp.metric == metric_name:
                return comp.delta
        return 0.0

    @staticmethod
    def _calculate_p_value(baseline_mappings: list[Any], shadow_mappings: list[Any]) -> float:
        """Estimate p-value using z-test approximation.

        Tests whether the difference in correction rates is statistically significant.
        """
        from plm_tcin_mapper_api.database.models import MappingStatus

        baseline_corrections = sum(
            1 for m in baseline_mappings if str(m.get("status", "")) == str(MappingStatus.CORRECTED)
        )
        shadow_corrections = sum(
            1 for m in shadow_mappings if str(m.get("status", "")) == str(MappingStatus.CORRECTED)
        )

        n1 = len(baseline_mappings)
        n2 = len(shadow_mappings)

        if n1 == 0 or n2 == 0:
            return 1.0

        p1 = baseline_corrections / n1
        p2 = shadow_corrections / n2
        p_pool = (baseline_corrections + shadow_corrections) / (n1 + n2)

        se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))

        if se == 0:
            return 1.0

        z = (p2 - p1) / se

        from scipy import stats

        p_value = 2 * (1 - stats.norm.cdf(abs(z)))
        return p_value

    @staticmethod
    def _generate_recommendation(
        comparisons: list[ShadowMetricComparison],
        overall_improvement: float,
        is_significant: bool,
    ) -> str:
        """Generate actionable recommendation based on comparison results."""
        improvements = [c for c in comparisons if c.is_improvement]
        degradations = [c for c in comparisons if not c.is_improvement]

        if overall_improvement > 0.02 and is_significant:
            return f"✅ RECOMMEND PROMOTION: {len(improvements)} metrics improved, {overall_improvement:.1%} overall improvement (p={p_value:.4f}, statistically significant)."
        elif overall_improvement > 0.01 and is_significant:
            return f"⚠️ MARGINAL IMPROVEMENT: {len(improvements)} improved but small effect size. Test on larger batch for confidence."
        elif overall_improvement > 0 and not is_significant:
            return f"❓ INCONCLUSIVE: {len(improvements)} metrics improved but not statistically significant (p={p_value:.4f}). More data needed."
        elif overall_improvement < -0.01:
            return f"❌ RECOMMEND REJECTION: {len(degradations)} metrics degraded. {overall_improvement:.1%} overall decline."
        else:
            return "➡️ NO CHANGE: Metrics unchanged between batches. Test with larger sample."
