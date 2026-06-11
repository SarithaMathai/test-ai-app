"""Eval service — computes accuracy metrics from the mappings collection."""

from __future__ import annotations

import asyncio

from ai_core.config import Settings
from ai_mongo import MongoClientManager

from plm_tcin_mapper.models.schemas import EvalResponse


class EvalService:
    def __init__(self, mongo: MongoClientManager, settings: Settings) -> None:
        self._mongo = mongo
        self._settings = settings

    async def run_eval(self) -> EvalResponse:
        return await asyncio.get_event_loop().run_in_executor(None, self._run_eval_sync)

    async def get_latest(self) -> EvalResponse | None:
        return await asyncio.get_event_loop().run_in_executor(None, self._get_latest_sync)

    def _run_eval_sync(self) -> EvalResponse:
        from plm_tcin_mapper.pipeline.evaluator import run_eval

        db = self._mongo.get_sync_db()
        result = run_eval(db=db, cfg=self._settings, persist=True)
        return self._to_response(result)

    def _get_latest_sync(self) -> EvalResponse | None:
        from plm_tcin_mapper.database.models import EvalRun

        db = self._mongo.get_sync_db()
        doc = db["eval_runs"].find_one(sort=[("created_at", -1)])
        if not doc:
            return None
        doc_copy = dict(doc)
        doc_copy["_id"] = str(doc_copy.get("_id", ""))
        run = EvalRun(**doc_copy)
        return self._to_response(run)

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
