"""Routes for shadow mode comparison — validate configuration changes before production."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from plm_tcin_mapper_api.models.schemas import ShadowComparisonResponse
from plm_tcin_mapper_api.pipeline.shadow_comparator import ShadowComparator

router = APIRouter(prefix="/shadow", tags=["shadow-mode"])


def get_shadow_comparator(mongo=None) -> ShadowComparator:
    """Dependency for shadow comparator service."""

    from plm_tcin_mapper_api.dependencies import get_mongo

    mongo_client = mongo or get_mongo()
    if isinstance(mongo_client, type):
        mongo_client = mongo_client()
    return ShadowComparator(mongo=mongo_client)


@router.post("/compare", response_model=ShadowComparisonResponse)
async def compare_batches(
    baseline_batch_id: str,
    shadow_batch_id: str,
    comparator: ShadowComparator = Depends(get_shadow_comparator),
) -> ShadowComparisonResponse:
    """Compare shadow batch against baseline batch to validate improvements."""
    return await comparator.compare(baseline_batch_id, shadow_batch_id)
