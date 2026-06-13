"""Threshold tuning service — analyzes eval metrics and proposes threshold adjustments."""

from __future__ import annotations

import asyncio
from typing import Any

from ai_mongo import MongoClientManager

from plm_tcin_mapper.database.models import (
    ExtendedEvalRun,
    ImpactEstimate,
    ProposalStatus,
    ThresholdChange,
    ThresholdProposal,
)
from plm_tcin_mapper.models.schemas import ThresholdProposalResponse
from plm_tcin_mapper.pipeline.impact_simulator import ImpactSimulator

_EXTENDED_EVAL_COL = "extended_eval_runs"
_THRESHOLD_PROPOSALS_COL = "threshold_proposals"


class ThresholdTuner:
    """Analyzes evaluation metrics to propose optimal threshold adjustments."""

    def __init__(self, mongo: MongoClientManager) -> None:
        self._mongo = mongo
        self._simulator = ImpactSimulator()

    async def analyze(self) -> ThresholdProposalResponse:
        """Analyze latest evaluation and generate threshold proposals."""
        return await asyncio.get_event_loop().run_in_executor(None, self._analyze_sync)

    def _analyze_sync(self) -> ThresholdProposalResponse:
        db = self._mongo.get_sync_db()
        eval_col = db[_EXTENDED_EVAL_COL]
        proposals_col = db[_THRESHOLD_PROPOSALS_COL]

        latest_eval = eval_col.find_one(sort=[("created_at", -1)])
        if not latest_eval:
            return ThresholdProposalResponse(
                status="error",
                message="No evaluation data available",
                proposals=[],
                proposals_generated=0,
            )

        eval_id = str(latest_eval.get("_id", ""))
        eval_run = ExtendedEvalRun(**latest_eval)

        proposals = self._generate_proposals(eval_run, eval_id)

        for proposal in proposals:
            proposals_col.insert_one(proposal.model_dump(by_alias=True))

        proposal_items = [
            {
                "id": p.id,
                "status": str(p.status),
                "proposal_type": p.proposal_type,
                "rationale": p.rationale,
                "changes": [
                    {
                        "parameter": c.parameter,
                        "current_value": c.current_value,
                        "proposed_value": c.proposed_value,
                        "delta": c.delta,
                    }
                    for c in p.changes
                ],
                "estimated_impact": [
                    {
                        "metric": m.metric,
                        "current_value": m.current_value,
                        "estimated_value": m.estimated_value,
                        "improvement": m.improvement,
                    }
                    for m in p.estimated_impact
                ],
                "confidence": p.confidence,
            }
            for p in proposals
        ]

        return ThresholdProposalResponse(
            status="ok",
            message=f"Generated {len(proposals)} proposals from latest evaluation",
            proposals=proposal_items,
            proposals_generated=len(proposals),
        )

    def _generate_proposals(self, eval_run: ExtendedEvalRun, eval_id: str) -> list[ThresholdProposal]:
        """Generate threshold adjustment proposals based on evaluation metrics."""
        proposals: list[ThresholdProposal] = []

        correction_rate = eval_run.correction_rate
        pct_high = eval_run.pct_high
        per_signal = eval_run.per_signal_accuracy

        supporting_metrics = {
            "correction_rate": correction_rate,
            "pct_high": pct_high,
            "avg_confidence": eval_run.avg_color_confidence,
        }

        if correction_rate > 0.30:
            proposal = self._propose_lower_auto_confirm_threshold(eval_run, eval_id, supporting_metrics)
            if proposal:
                proposals.append(proposal)

        if pct_high < 0.35:
            proposal = self._propose_raise_llm_threshold(eval_run, eval_id, supporting_metrics)
            if proposal:
                proposals.append(proposal)

        if eval_run.llm_impact and eval_run.llm_impact.llm_correction_rate > 0.20:
            proposal = self._propose_adjust_llm_fallback(eval_run, eval_id, supporting_metrics)
            if proposal:
                proposals.append(proposal)

        if correction_rate > 0.25 and pct_high > 0.40:
            proposal = self._propose_fuzzy_weight_reduction(eval_run, eval_id, supporting_metrics)
            if proposal:
                proposals.append(proposal)

        if eval_run.confidence_calibration_error > 0.15:
            proposal = self._propose_confidence_recalibration(eval_run, eval_id, supporting_metrics)
            if proposal:
                proposals.append(proposal)

        return proposals

    def _propose_lower_auto_confirm_threshold(
        self,
        eval_run: ExtendedEvalRun,
        eval_id: str,
        supporting_metrics: dict[str, float],
    ) -> ThresholdProposal | None:
        """Propose lowering auto_confirm_threshold when correction rate is high."""
        correction_rate = eval_run.correction_rate

        if correction_rate <= 0.30:
            return None

        current_value = 0.85
        proposed_value = 0.88

        if correction_rate > 0.35:
            proposed_value = 0.90

        delta = proposed_value - current_value

        impact_estimate = self._simulator.estimate_impact(
            "auto_confirm_threshold",
            current_value,
            proposed_value,
            correction_rate,
        )

        changes = [
            ThresholdChange(
                parameter="auto_confirm_threshold",
                current_value=current_value,
                proposed_value=proposed_value,
                delta=delta,
            )
        ]

        estimated_impact = [
            ImpactEstimate(
                metric="correction_rate",
                current_value=correction_rate,
                estimated_value=impact_estimate.get("correction_rate", correction_rate * 0.9),
                improvement=correction_rate - impact_estimate.get("correction_rate", correction_rate * 0.9),
            )
        ]

        confidence = min(0.95, 0.70 + (correction_rate - 0.30) * 2)

        rationale = (
            f"Correction rate is {correction_rate:.1%} (target: <25%). "
            f"Raising auto_confirm_threshold from {current_value} to {proposed_value} "
            f"will be more conservative, catching edge cases before AUTO_CONFIRM. "
            f"Estimated improvement: {estimated_impact[0].improvement:.1%}."
        )

        return ThresholdProposal(
            status=ProposalStatus.PENDING,
            eval_run_id=eval_id,
            proposal_type="RAISE_AUTO_CONFIRM_THRESHOLD",
            rationale=rationale,
            changes=changes,
            estimated_impact=estimated_impact,
            confidence=confidence,
            supporting_metrics=supporting_metrics,
        )

    def _propose_raise_llm_threshold(
        self,
        eval_run: ExtendedEvalRun,
        eval_id: str,
        supporting_metrics: dict[str, float],
    ) -> ThresholdProposal | None:
        """Propose raising llm_fallback_threshold when HIGH confidence percentage is low."""
        pct_high = eval_run.pct_high

        if pct_high >= 0.40:
            return None

        current_value = 0.60
        proposed_value = 0.70 if pct_high < 0.30 else 0.65

        delta = proposed_value - current_value

        impact_estimate = self._simulator.estimate_impact(
            "llm_fallback_threshold",
            current_value,
            proposed_value,
            eval_run.correction_rate,
        )

        changes = [
            ThresholdChange(
                parameter="llm_fallback_threshold",
                current_value=current_value,
                proposed_value=proposed_value,
                delta=delta,
            )
        ]

        estimated_high_pct = impact_estimate.get("pct_high", pct_high * 1.15)
        estimated_impact = [
            ImpactEstimate(
                metric="pct_high_confidence",
                current_value=pct_high,
                estimated_value=estimated_high_pct,
                improvement=estimated_high_pct - pct_high,
            )
        ]

        confidence = min(0.90, 0.60 + (0.40 - pct_high) * 3)

        rationale = (
            f"Only {pct_high:.1%} of mappings have HIGH confidence (target: >40%). "
            f"Raising llm_fallback_threshold from {current_value} to {proposed_value} "
            f"triggers LLM for more cases, potentially improving confidence distribution. "
            f"Estimated improvement: {estimated_impact[0].improvement:.1%}."
        )

        return ThresholdProposal(
            status=ProposalStatus.PENDING,
            eval_run_id=eval_id,
            proposal_type="RAISE_LLM_FALLBACK_THRESHOLD",
            rationale=rationale,
            changes=changes,
            estimated_impact=estimated_impact,
            confidence=confidence,
            supporting_metrics=supporting_metrics,
        )

    def _propose_adjust_llm_fallback(
        self,
        eval_run: ExtendedEvalRun,
        eval_id: str,
        supporting_metrics: dict[str, float],
    ) -> ThresholdProposal | None:
        """Propose adjusting LLM fallback based on LLM performance."""
        if not eval_run.llm_impact:
            return None

        llm_correction_rate = eval_run.llm_impact.llm_correction_rate

        if llm_correction_rate <= 0.15:
            proposed_direction = "LOWER"
            current_value = 0.60
            proposed_value = 0.50
        elif llm_correction_rate <= 0.20:
            proposed_direction = "MAINTAIN"
            return None
        else:
            proposed_direction = "RAISE"
            current_value = 0.60
            proposed_value = 0.70

        delta = proposed_value - current_value

        impact_estimate = self._simulator.estimate_impact(
            "llm_fallback_threshold",
            current_value,
            proposed_value,
            eval_run.correction_rate,
        )

        changes = [
            ThresholdChange(
                parameter="llm_fallback_threshold",
                current_value=current_value,
                proposed_value=proposed_value,
                delta=delta,
            )
        ]

        estimated_correction = impact_estimate.get("correction_rate", eval_run.correction_rate)
        estimated_impact = [
            ImpactEstimate(
                metric="correction_rate",
                current_value=eval_run.correction_rate,
                estimated_value=estimated_correction,
                improvement=eval_run.correction_rate - estimated_correction,
            )
        ]

        confidence = 0.75

        rationale = (
            f"LLM correction rate is {llm_correction_rate:.1%}. "
            f"{proposed_direction}ing threshold from {current_value} to {proposed_value} "
            f"{'uses LLM more aggressively' if proposed_direction == 'LOWER' else 'uses LLM more conservatively'}. "
            f"Expected impact on overall correction rate: {estimated_impact[0].improvement:.1%}."
        )

        return ThresholdProposal(
            status=ProposalStatus.PENDING,
            eval_run_id=eval_id,
            proposal_type=f"ADJUST_LLM_FALLBACK_{proposed_direction}",
            rationale=rationale,
            changes=changes,
            estimated_impact=estimated_impact,
            confidence=confidence,
            supporting_metrics=supporting_metrics,
        )

    def _propose_fuzzy_weight_reduction(
        self,
        eval_run: ExtendedEvalRun,
        eval_id: str,
        supporting_metrics: dict[str, float],
    ) -> ThresholdProposal | None:
        """Propose reducing fuzzy matching weight if it's a weak signal."""
        fuzzy_metric = eval_run.per_signal_accuracy.get("fuzzy_match")
        if not fuzzy_metric or fuzzy_metric.correction_rate < 0.40:
            return None

        current_value = 1.0
        proposed_value = 0.5

        delta = proposed_value - current_value

        impact_estimate = self._simulator.estimate_impact(
            "fuzzy_match_weight",
            current_value,
            proposed_value,
            eval_run.correction_rate,
        )

        changes = [
            ThresholdChange(
                parameter="fuzzy_match_weight",
                current_value=current_value,
                proposed_value=proposed_value,
                delta=delta,
            )
        ]

        estimated_correction = impact_estimate.get("correction_rate", eval_run.correction_rate * 0.95)
        estimated_impact = [
            ImpactEstimate(
                metric="correction_rate",
                current_value=eval_run.correction_rate,
                estimated_value=estimated_correction,
                improvement=eval_run.correction_rate - estimated_correction,
            )
        ]

        confidence = 0.80

        rationale = (
            f"Fuzzy matching signal has {fuzzy_metric.correction_rate:.1%} correction rate (weak). "
            f"Reducing its weight from {current_value} to {proposed_value} deprioritizes fuzzy fallback, "
            f"forcing reliance on stronger signals (token/keyword). "
            f"Expected impact: {estimated_impact[0].improvement:.1%} improvement."
        )

        return ThresholdProposal(
            status=ProposalStatus.PENDING,
            eval_run_id=eval_id,
            proposal_type="REDUCE_FUZZY_WEIGHT",
            rationale=rationale,
            changes=changes,
            estimated_impact=estimated_impact,
            confidence=confidence,
            supporting_metrics=supporting_metrics,
        )

    def _propose_confidence_recalibration(
        self,
        eval_run: ExtendedEvalRun,
        eval_id: str,
        supporting_metrics: dict[str, float],
    ) -> ThresholdProposal | None:
        """Propose confidence recalibration when calibration error is high."""
        ece = eval_run.confidence_calibration_error

        if ece <= 0.15:
            return None

        changes = [
            ThresholdChange(
                parameter="confidence_recalibration_enabled",
                current_value=0.0,
                proposed_value=1.0,
                delta=1.0,
            )
        ]

        impact_estimate = self._simulator.estimate_calibration_improvement(ece)

        estimated_ece = impact_estimate.get("ece", ece * 0.7)
        estimated_impact = [
            ImpactEstimate(
                metric="confidence_calibration_error",
                current_value=ece,
                estimated_value=estimated_ece,
                improvement=ece - estimated_ece,
            )
        ]

        confidence = 0.70

        rationale = (
            f"Confidence calibration error is {ece:.3f} (target: <0.10). "
            f"Enabling confidence recalibration will rescale confidence scores "
            f"to better match actual accuracy. "
            f"Expected improvement: ECE {ece:.3f} → {estimated_ece:.3f}."
        )

        return ThresholdProposal(
            status=ProposalStatus.PENDING,
            eval_run_id=eval_id,
            proposal_type="ENABLE_CONFIDENCE_RECALIBRATION",
            rationale=rationale,
            changes=changes,
            estimated_impact=estimated_impact,
            confidence=confidence,
            supporting_metrics=supporting_metrics,
        )

    async def apply_proposal(self, proposal_id: str) -> dict[str, Any]:
        """Apply a proposal by updating configuration."""
        return await asyncio.get_event_loop().run_in_executor(None, self._apply_proposal_sync, proposal_id)

    def _apply_proposal_sync(self, proposal_id: str) -> dict[str, Any]:
        db = self._mongo.get_sync_db()
        proposals_col = db[_THRESHOLD_PROPOSALS_COL]

        proposal_doc = proposals_col.find_one({"_id": proposal_id})
        if not proposal_doc:
            return {"status": "error", "message": f"Proposal {proposal_id} not found"}

        if proposal_doc.get("status") == str(ProposalStatus.APPLIED):
            return {"status": "error", "message": "Proposal already applied"}

        import os
        from pathlib import Path

        import yaml

        config_dir = os.environ.get("APP_CONFIG_DIR", "config")
        config_path = Path(config_dir) / "base.yaml"

        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            return {"status": "error", "message": f"Failed to read config: {e}"}

        changes = proposal_doc.get("changes", [])
        for change in changes:
            param = change.get("parameter", "")
            proposed_value = change.get("proposed_value")

            if param.startswith("auto_confirm"):
                config.setdefault("matching", {})["auto_confirm_threshold"] = proposed_value
            elif param.startswith("llm_fallback"):
                config.setdefault("matching", {})["llm_fallback_threshold"] = proposed_value
            elif param.startswith("fuzzy"):
                config.setdefault("scorer", {})["fuzzy_match_weight"] = proposed_value
            elif param.startswith("confidence"):
                config.setdefault("matching", {})["enable_confidence_recalibration"] = bool(proposed_value)

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            return {"status": "error", "message": f"Failed to write config: {e}"}

        proposals_col.update_one(
            {"_id": proposal_id},
            {
                "$set": {
                    "status": str(ProposalStatus.APPLIED),
                    "applied_at": __import__("datetime").datetime.now(__import__("datetime").UTC),
                }
            },
        )

        return {
            "status": "ok",
            "message": f"Proposal applied: {len(changes)} configuration changes made",
        }

    async def list_proposals(self, status: str | None = None) -> dict[str, Any]:
        """List proposals, optionally filtered by status."""
        return await asyncio.get_event_loop().run_in_executor(None, self._list_proposals_sync, status)

    def _list_proposals_sync(self, status: str | None = None) -> dict[str, Any]:
        db = self._mongo.get_sync_db()
        proposals_col = db[_THRESHOLD_PROPOSALS_COL]

        query = {}
        if status:
            query["status"] = status

        proposals = list(proposals_col.find(query).sort("created_at", -1))

        items = [
            {
                "id": str(p.get("_id", "")),
                "status": p.get("status", "PENDING"),
                "proposal_type": p.get("proposal_type", ""),
                "rationale": p.get("rationale", ""),
                "changes": p.get("changes", []),
                "estimated_impact": p.get("estimated_impact", []),
                "confidence": p.get("confidence", 0.0),
                "created_at": str(p.get("created_at", "")),
            }
            for p in proposals
        ]

        return {"total": len(items), "proposals": items}
