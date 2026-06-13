"""Impact simulator — estimates the effects of threshold changes on metrics."""

from __future__ import annotations


class ImpactSimulator:
    """Simulates the impact of threshold adjustments on evaluation metrics."""

    def estimate_impact(
        self,
        parameter: str,
        current_value: float,
        proposed_value: float,
        current_correction_rate: float,
    ) -> dict[str, float]:
        """Estimate how a threshold change affects metrics.

        Returns estimated values for affected metrics.
        """
        if parameter == "auto_confirm_threshold":
            return self._estimate_auto_confirm_impact(current_value, proposed_value, current_correction_rate)
        elif parameter == "llm_fallback_threshold":
            return self._estimate_llm_threshold_impact(current_value, proposed_value, current_correction_rate)
        elif parameter == "fuzzy_match_weight":
            return self._estimate_fuzzy_weight_impact(current_value, proposed_value, current_correction_rate)
        else:
            return {}

    def estimate_calibration_improvement(self, current_ece: float) -> dict[str, float]:
        """Estimate ECE improvement from recalibration."""
        improved_ece = max(0.05, current_ece * 0.6)
        return {"ece": improved_ece}

    @staticmethod
    def _estimate_auto_confirm_impact(
        current_value: float,
        proposed_value: float,
        current_correction_rate: float,
    ) -> dict[str, float]:
        """Estimate impact of raising auto_confirm_threshold.

        Higher threshold = fewer AUTO_CONFIRM, more NEEDS_REVIEW = fewer missed errors.
        Estimated correction rate improvement: 5-15% depending on delta.
        """
        delta = proposed_value - current_value

        if delta <= 0:
            return {}

        improvement = delta * 12

        estimated_correction = max(0.0, current_correction_rate - improvement)

        return {
            "correction_rate": estimated_correction,
            "pct_high": 0.0,
        }

    @staticmethod
    def _estimate_llm_threshold_impact(
        current_value: float,
        proposed_value: float,
        current_correction_rate: float,
    ) -> dict[str, float]:
        """Estimate impact of raising/lowering llm_fallback_threshold.

        Raising threshold = use LLM for more cases = potentially higher pct_high.
        Lowering = use LLM only for very low confidence = potentially lower correction.
        """
        delta = proposed_value - current_value

        if delta > 0:
            pct_high_improvement = min(0.15, delta * 2)
            correction_improvement = delta * 3
        else:
            pct_high_improvement = delta * 2
            correction_improvement = delta * 5

        estimated_high = max(0.0, 0.35 + pct_high_improvement)
        estimated_correction = max(0.0, current_correction_rate - correction_improvement)

        return {
            "pct_high": estimated_high,
            "correction_rate": estimated_correction,
        }

    @staticmethod
    def _estimate_fuzzy_weight_impact(
        current_value: float,
        proposed_value: float,
        current_correction_rate: float,
    ) -> dict[str, float]:
        """Estimate impact of reducing fuzzy matching weight.

        Lower weight = fuzzy matches have less influence = rely more on token/keyword.
        Expected: 3-8% improvement in correction rate if fuzzy is weak signal.
        """
        delta = current_value - proposed_value

        if delta <= 0:
            return {}

        improvement = min(0.08, delta * 5)

        estimated_correction = max(0.0, current_correction_rate - improvement)

        return {
            "correction_rate": estimated_correction,
        }
