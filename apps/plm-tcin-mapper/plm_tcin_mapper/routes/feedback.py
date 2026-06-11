"""Human-in-the-loop feedback route."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from plm_tcin_mapper.dependencies import FeedbackServiceDep
from plm_tcin_mapper.models.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest, service: FeedbackServiceDep) -> FeedbackResponse:
    """Submit human feedback (CONFIRM / REJECT / CORRECT) for a mapping."""
    valid_actions = {"CONFIRM", "REJECT", "CORRECT"}
    if request.action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"action must be one of {valid_actions}")
    return await service.submit(request)
