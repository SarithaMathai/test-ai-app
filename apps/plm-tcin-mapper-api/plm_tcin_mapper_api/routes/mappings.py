"""Mapping pipeline routes."""

from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Query

from plm_tcin_mapper_api.dependencies import MappingServiceDep, MongoDep
from plm_tcin_mapper_api.models.schemas import MappingRunRequest, MappingRunResponse, MappingsResponse

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


@router.get("/mappings/summary")
async def get_mapping_summary(department: str | None = Query(None), mongo: MongoDep = None) -> dict:
    """
    Get department-level summary of mappings (count by status, avg confidence, etc).

    Query params:
      department: Optional department ID to filter by

    Returns:
      {
        "department": str | None,
        "total": int,
        "by_status": {status: count},
        "avg_confidence": float,
        "high_confidence_count": int,
        "low_confidence_count": int
      }
    """
    db = await mongo.get_db()
    collection = db.mappings

    filter_query = {}
    if department:
        filter_query["department"] = department

    pipeline = [
        {"$match": filter_query},
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1},
            }
        },
    ]

    status_counts = {}
    async for doc in collection.aggregate(pipeline):
        status_counts[doc["_id"]] = doc["count"]

    total = sum(status_counts.values())

    # Get confidence metrics
    conf_pipeline = [
        {"$match": filter_query},
        {
            "$group": {
                "_id": None,
                "avg_confidence": {"$avg": "$confidence_score"},
                "high_conf": {"$sum": {"$cond": [{"$gte": ["$confidence_score", 0.8]}, 1, 0]}},
                "low_conf": {"$sum": {"$cond": [{"$lt": ["$confidence_score", 0.5]}, 1, 0]}},
            }
        },
    ]

    conf_result = await collection.aggregate(conf_pipeline).to_list(1)
    conf_metrics = conf_result[0] if conf_result else {"avg_confidence": 0, "high_conf": 0, "low_conf": 0}

    return {
        "department": department,
        "total": total,
        "by_status": status_counts,
        "avg_confidence": round(conf_metrics.get("avg_confidence", 0), 2),
        "high_confidence_count": conf_metrics.get("high_conf", 0),
        "low_confidence_count": conf_metrics.get("low_conf", 0),
    }


@router.post("/mappings/{mapping_id}/clear")
async def clear_mapping(mapping_id: str, mongo: MongoDep = None) -> dict:
    """
    Clear a mapping by setting its status to NO_MATCH.

    Path params:
      mapping_id: MongoDB ObjectId of the mapping

    Returns:
      {
        "id": str,
        "status": "cleared" | "not_found"
      }
    """
    db = await mongo.get_db()
    collection = db.mappings

    try:
        obj_id = ObjectId(mapping_id)
    except Exception:
        return {"id": mapping_id, "status": "invalid_id"}

    result = await collection.update_one(
        {"_id": obj_id},
        {"$set": {"status": "NO_MATCH"}},
    )

    if result.matched_count == 0:
        return {"id": mapping_id, "status": "not_found"}

    return {"id": mapping_id, "status": "cleared"}
