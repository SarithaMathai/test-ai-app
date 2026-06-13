"""GET /health — liveness probe."""

from __future__ import annotations

from fastapi import APIRouter

from plm_tcin_mapper_api.dependencies import LLMClientDep, MongoDep, SettingsDep
from plm_tcin_mapper_api.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: SettingsDep, llm: LLMClientDep, mongo: MongoDep) -> HealthResponse:
    mongo_ok = await mongo.ping()
    return HealthResponse(
        status="ok",
        llm_provider=settings.llm.provider,
        llm_model=settings.llm.model,
        mongo_ok=mongo_ok,
    )
