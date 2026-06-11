"""Routes for extended evaluation — detailed accuracy metrics by signal, department, and LLM impact."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from plm_tcin_mapper.dependencies import EvalServiceDep
from plm_tcin_mapper.models.schemas import ExtendedEvalResponse

router = APIRouter(prefix="/eval", tags=["evaluation"])


@router.post("/detailed", response_model=ExtendedEvalResponse)
async def run_detailed_eval(
    service: EvalServiceDep,
) -> ExtendedEvalResponse:
    """Compute detailed evaluation metrics including per-signal, per-department, and LLM impact analysis."""
    return await service.run_detailed_eval()


@router.get("/detailed/latest", response_model=ExtendedEvalResponse | None)
async def get_latest_detailed_eval(
    service: EvalServiceDep,
) -> ExtendedEvalResponse | None:
    """Get the most recent detailed evaluation run."""
    return await service.get_latest_detailed_eval()
