"""Evaluation routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from plm_tcin_mapper.dependencies import EvalServiceDep
from plm_tcin_mapper.models.schemas import EvalResponse

router = APIRouter(tags=["eval"])


@router.post("/eval/run", response_model=EvalResponse)
async def run_eval(service: EvalServiceDep) -> EvalResponse:
    """Compute evaluation metrics and guardrail alerts from the mappings collection."""
    return await service.run_eval()


@router.get("/eval/latest", response_model=EvalResponse)
async def latest_eval(service: EvalServiceDep) -> EvalResponse:
    """Return the most recent evaluation snapshot."""
    result = await service.get_latest()
    if result is None:
        raise HTTPException(status_code=404, detail="No eval runs found. Run POST /api/v1/eval/run first.")
    return result
