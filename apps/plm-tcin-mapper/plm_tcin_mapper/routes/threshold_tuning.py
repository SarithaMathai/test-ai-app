"""Routes for threshold tuning — analyze metrics and propose configuration improvements."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from plm_tcin_mapper.dependencies import get_threshold_tuner_service
from plm_tcin_mapper.models.schemas import (
    ThresholdProposalApplyRequest,
    ThresholdProposalApplyResponse,
    ThresholdProposalListResponse,
    ThresholdProposalResponse,
)
from plm_tcin_mapper.pipeline.threshold_tuner import ThresholdTuner

router = APIRouter(prefix="/threshold-tuning", tags=["threshold-tuning"])


@router.post("/analyze", response_model=ThresholdProposalResponse)
async def analyze_for_proposals(
    service: ThresholdTuner = Depends(get_threshold_tuner_service),
) -> ThresholdProposalResponse:
    """Analyze latest evaluation and generate threshold improvement proposals."""
    return await service.analyze()


@router.get("/proposals", response_model=ThresholdProposalListResponse)
async def list_proposals(
    status: str | None = None,
    service: ThresholdTuner = Depends(get_threshold_tuner_service),
) -> ThresholdProposalListResponse:
    """List all threshold proposals, optionally filtered by status."""
    result = await service.list_proposals(status)
    return ThresholdProposalListResponse(**result)


@router.post("/proposals/{proposal_id}/apply", response_model=ThresholdProposalApplyResponse)
async def apply_proposal(
    proposal_id: str,
    request: ThresholdProposalApplyRequest | None = None,
    service: ThresholdTuner = Depends(get_threshold_tuner_service),
) -> ThresholdProposalApplyResponse:
    """Apply a proposal by updating configuration files."""
    result = await service.apply_proposal(proposal_id)
    return ThresholdProposalApplyResponse(
        status=result.get("status", "error"),
        proposal_id=proposal_id,
        message=result.get("message", "Unknown error"),
    )
