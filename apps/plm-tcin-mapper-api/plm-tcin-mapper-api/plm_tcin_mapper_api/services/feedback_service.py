"""Feedback service — records human-in-the-loop review actions."""

from __future__ import annotations

import asyncio

from ai_mongo import MongoClientManager

from plm_tcin_mapper_api.database.models import FeedbackAction, FeedbackRecord
from plm_tcin_mapper_api.models.schemas import FeedbackRequest, FeedbackResponse

_FEEDBACK_COL = "feedback"
_MAPPING_COL = "mappings"


class FeedbackService:
    def __init__(self, mongo: MongoClientManager) -> None:
        self._mongo = mongo

    async def submit(self, request: FeedbackRequest) -> FeedbackResponse:
        return await asyncio.get_event_loop().run_in_executor(None, self._submit_sync, request)

    def _submit_sync(self, request: FeedbackRequest) -> FeedbackResponse:
        db = self._mongo.get_sync_db()

        action = FeedbackAction(request.action)
        was_correct = action == FeedbackAction.CONFIRM

        # Load mapping from DB to enrich feedback context
        mapping = db[_MAPPING_COL].find_one({"_id": request.mapping_id})

        record = FeedbackRecord(
            mapping_id=request.mapping_id,
            pid=request.pid,
            tcin_id=request.tcin_id,
            action=action,
            reviewer=request.reviewer,
            notes=request.notes,
            # Enrich with context from mapping
            tcin_color=mapping.get("tcin_color") if mapping else None,
            tcin_color_name=mapping.get("tcin_color_name") if mapping else None,
            tcin_size=mapping.get("tcin_size") if mapping else None,
            department_ids=mapping.get("department_ids", []) if mapping else [],
            match_round=str(mapping.get("match_round")) if mapping and mapping.get("match_round") else None,
            original_confidence_tier=str(mapping.get("confidence_tier"))
            if mapping and mapping.get("confidence_tier")
            else None,
            original_impression_name=mapping.get("matched_impression_name") if mapping else None,
            original_color_confidence=mapping.get("color_confidence") if mapping else None,
            suggested_impression_id=request.suggested_impression_id,
            suggested_impression_name=request.suggested_impression_name,
            was_correct=was_correct,
        )

        doc = record.model_dump(by_alias=True)
        result = db[_FEEDBACK_COL].insert_one(doc)

        # Update mapping status to reflect the human decision
        status_map = {
            FeedbackAction.CONFIRM: "CONFIRMED",
            FeedbackAction.REJECT: "REJECTED",
            FeedbackAction.CORRECT: "CORRECTED",
        }
        db[_MAPPING_COL].update_one(
            {"_id": request.mapping_id},
            {"$set": {"status": status_map[action]}},
        )

        return FeedbackResponse(status="ok", feedback_id=str(result.inserted_id))
