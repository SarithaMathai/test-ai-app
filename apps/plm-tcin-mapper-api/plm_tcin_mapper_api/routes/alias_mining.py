"""Routes for alias mining — analyze feedback to propose keyword improvements."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from plm_tcin_mapper_api.dependencies import get_alias_mining_service
from plm_tcin_mapper_api.models.schemas import (
    AliasMiningAnalyzeRequest,
    AliasMiningAnalyzeResponse,
    AliasMiningApplyRequest,
    AliasMiningApplyResponse,
    AliasMiningProposalsResponse,
)
from plm_tcin_mapper_api.services.alias_mining_service import AliasMiningService

router = APIRouter(prefix="/alias-mining", tags=["alias-mining"])


@router.post("/analyze", response_model=AliasMiningAnalyzeResponse)
async def analyze_feedback(
    request: AliasMiningAnalyzeRequest,
    service: AliasMiningService = Depends(get_alias_mining_service),
) -> AliasMiningAnalyzeResponse:
    """Analyze feedback records to identify keyword patterns and generate improvement proposals."""
    return await service.analyze(request)


@router.get("/proposals", response_model=AliasMiningProposalsResponse)
async def list_proposals(
    status: str | None = None,
    service: AliasMiningService = Depends(get_alias_mining_service),
) -> AliasMiningProposalsResponse:
    """List all alias mining proposals, optionally filtered by status."""
    result = await service.list_proposals(status)
    return AliasMiningProposalsResponse(**result)


@router.post("/proposals/{proposal_id}/apply", response_model=AliasMiningApplyResponse)
async def apply_proposal(
    proposal_id: str,
    request: AliasMiningApplyRequest | None = None,
    service: AliasMiningService = Depends(get_alias_mining_service),
) -> AliasMiningApplyResponse:
    """Apply a proposal by updating alias_overrides.yaml with the new keyword mapping."""
    result = await service.apply_proposal(proposal_id)
    return AliasMiningApplyResponse(
        status=result.get("status", "error"),
        proposal_id=proposal_id,
        message=result.get("message", "Unknown error"),
    )
