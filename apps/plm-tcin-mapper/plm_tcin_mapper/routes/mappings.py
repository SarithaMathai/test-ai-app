"""Mapping pipeline routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from plm_tcin_mapper.dependencies import MappingServiceDep
from plm_tcin_mapper.models.schemas import MappingRunRequest, MappingRunResponse, MappingsResponse

router = APIRouter(tags=["mappings"])


@router.post("/mappings/run", response_model=MappingRunResponse)
async def run_mappings(request: MappingRunRequest, service: MappingServiceDep) -> MappingRunResponse:
    """Trigger the matching pipeline for one PID, a department, or all unmatched PIDs."""
    return await service.run(request)


@router.get("/mappings", response_model=MappingsResponse)
async def list_mappings(
    service: MappingServiceDep,
    pid: str | None = Query(None),
    status: str | None = Query(None),
    department: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> MappingsResponse:
    """Query mappings with optional filters."""
    return await service.list_mappings(pid=pid, status=status, department=department, page=page, page_size=page_size)
