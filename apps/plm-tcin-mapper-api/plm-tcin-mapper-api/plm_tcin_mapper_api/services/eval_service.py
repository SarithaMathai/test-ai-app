"""Eval service — computes accuracy metrics from the mappings collection."""

from __future__ import annotations

import asyncio

from ai_core.config import Settings
from ai_mongo import MongoClientManager

from plm_tcin_mapper_api.models.schemas import EvalResponse


class EvalService:
    def __init__(self, mongo: MongoClientManager, settings: Settings) -> None:
        self._mongo = mongo
        self._settings = settings

    async def run_eval(self) -> EvalResponse:
        return await asyncio.get_event_loop().run_in_executor(None, self._run_eval_sync)

    async def get_latest(self) -> EvalResponse | None:
        return await asyncio.get_event_loop().run_in_executor(None, self._get_latest_sync)

    async def run_detailed_eval(self):
        return await asyncio.get_event_loop().run_in_executor(None, self._run_detailed_eval_sync)

    async def get_latest_detailed_eval(self):
        return await asyncio.get_event_loop().run_in_executor(None, self._get_latest_detailed_eval_sync)

    def _run_eval_sync(self) -> EvalResponse:
        from plm_tcin_mapper_api.pipeline.evaluator import run_eval

        db = self._mongo.get_sync_db()
        result = run_eval(db=db, cfg=self._settings, persist=True)
        return self._to_response(result)

    def _get_latest_sync(self) -> EvalResponse | None:
        from plm_tcin_mapper_api.database.models import EvalRun

        db = self._mongo.get_sync_db()
        doc = db["eval_runs"].find_one(sort=[("created_at", -1)])
        if not doc:
            return None
        doc_copy = dict(doc)
        doc_copy["_id"] = str(doc_copy.get("_id", ""))
        run = EvalRun(**doc_copy)
        return self._to_response(run)

    def _run_detailed_eval_sync(self):
        from plm_tcin_mapper_api.pipeline.extended_evaluator import run_extended_eval

        db = self._mongo.get_sync_db()
        result = run_extended_eval(db=db, persist=True)
        return self._to_detailed_response(result)

    def _get_latest_detailed_eval_sync(self):
        from plm_tcin_mapper_api.database.models import ExtendedEvalRun

        db = self._mongo.get_sync_db()
        doc = db["extended_eval_runs"].find_one(sort=[("created_at", -1)])
        if not doc:
            return None
        doc_copy = dict(doc)
        doc_copy["_id"] = str(doc_copy.get("_id", ""))
        run = ExtendedEvalRun(**doc_copy)
        return self._to_detailed_response(run)

    @staticmethod
    def _to_response(run) -> EvalResponse:
        return EvalResponse(
            id=str(getattr(run, "id", "")),
            total_mappings=run.total_mappings,
            by_status={str(k): v for k, v in run.by_status.items()},
            by_tier={str(k): v for k, v in run.by_tier.items()},
            pct_high=run.pct_high,
            pct_good=run.pct_good,
            pct_fair=run.pct_fair,
            pct_low=run.pct_low,
            avg_color_confidence=run.avg_color_confidence,
            correction_rate=run.correction_rate,
            guardrail_alerts=run.guardrail_alerts,
        )

    @staticmethod
    def _to_detailed_response(run):
        from plm_tcin_mapper_api.models.schemas import (
            DepartmentMetricsItem,
            ExtendedEvalResponse,
            LLMImpactItem,
            SignalAccuracyItem,
        )

        signal_accuracy_items = {
            signal: SignalAccuracyItem(
                signal_type=metric.signal_type,
                occurrences=metric.occurrences,
                corrections=metric.corrections,
                correction_rate=metric.correction_rate,
                avg_confidence=metric.avg_confidence,
                confidence_by_tier=metric.confidence_by_tier,
            )
            for signal, metric in run.per_signal_accuracy.items()
        }

        dept_items = [
            DepartmentMetricsItem(
                department=metric.department,
                total_mappings=metric.total_mappings,
                pct_high_confidence=metric.pct_high_confidence,
                correction_rate=metric.correction_rate,
                avg_confidence=metric.avg_confidence,
                by_match_round=metric.by_match_round,
            )
            for metric in run.per_department_metrics
        ]

        llm_item = None
        if run.llm_impact:
            llm_item = LLMImpactItem(
                total_llm_calls=run.llm_impact.total_llm_calls,
                llm_corrected=run.llm_impact.llm_corrected,
                llm_correction_rate=run.llm_impact.llm_correction_rate,
                llm_avg_confidence=run.llm_impact.llm_avg_confidence,
                deterministic_corrected=run.llm_impact.deterministic_corrected,
                deterministic_correction_rate=run.llm_impact.deterministic_correction_rate,
                llm_vs_deterministic_improvement=run.llm_impact.llm_vs_deterministic_improvement,
            )

        return ExtendedEvalResponse(
            id=str(getattr(run, "id", "")),
            total_mappings=run.total_mappings,
            by_status={str(k): v for k, v in run.by_status.items()},
            by_tier={str(k): v for k, v in run.by_tier.items()},
            pct_high=run.pct_high,
            pct_good=run.pct_good,
            pct_fair=run.pct_fair,
            pct_low=run.pct_low,
            avg_color_confidence=run.avg_color_confidence,
            correction_rate=run.correction_rate,
            per_signal_accuracy=signal_accuracy_items,
            per_department_metrics=dept_items,
            llm_impact=llm_item,
            confidence_calibration_error=run.confidence_calibration_error,
            high_confidence_actual_correction_rate=run.high_confidence_actual_correction_rate,
            low_confidence_actual_correction_rate=run.low_confidence_actual_correction_rate,
            guardrail_alerts=run.guardrail_alerts,
        )
