from fastapi import APIRouter

from spark_think_tank_ai.dependencies import LLMClientDep
from spark_think_tank_ai.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(llm: LLMClientDep) -> HealthResponse:
    """Liveness probe — returns provider and model so you can confirm config."""
    return HealthResponse(
        status="ok",
        provider=llm.provider,
        model=llm.model_name,
    )
