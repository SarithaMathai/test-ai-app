"""CSV ingestion route."""

from __future__ import annotations

from fastapi import APIRouter

from plm_tcin_mapper_api.dependencies import IngestionServiceDep
from plm_tcin_mapper_api.models.schemas import IngestRequest, IngestResponse

router = APIRouter(tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest, service: IngestionServiceDep) -> IngestResponse:
    """Ingest normalized CSV data from the configured data directory into MongoDB."""
    return await service.run(request)
