"""GET /api/v1/variations — fetch distinct impression variations for a given PID."""

from __future__ import annotations

from fastapi import APIRouter, Query

from plm_tcin_mapper_api.dependencies import MongoDep

router = APIRouter(tags=["variations"])


@router.get("/variations")
async def get_variations(pid: str = Query(...), mongo: MongoDep = None) -> dict:
    """
    Get distinct impression names for a given PID.

    Query params:
      pid: Product ID to fetch variations for

    Returns:
      {
        "pid": str,
        "variations": [list of distinct impression names]
      }
    """
    db = await mongo.get_db()
    variations = await db.variation_records.distinct("impression_name", {"pid": pid})
    return {"pid": pid, "variations": sorted(variations)}
