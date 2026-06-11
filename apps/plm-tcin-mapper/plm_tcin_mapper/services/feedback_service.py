"""Feedback service — records human-in-the-loop review actions."""

from __future__ import annotations

import asyncio

from ai_mongo import MongoClientManager

from plm_tcin_mapper.database.models import FeedbackAction, FeedbackRecord
from plm_tcin_mapper.models.schemas import FeedbackRequest, FeedbackResponse

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

        record = FeedbackRecord(
            mapping_id=request.mapping_id,
            pid=request.pid,
            tcin_id=request.tcin_id,
            action=action,
            reviewer=request.reviewer,
            notes=request.notes,
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
