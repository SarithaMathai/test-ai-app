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
    page_size: int = Query(1000, ge=1, le=5000),
) -> MappingsResponse:
    """Query mappings with optional filters."""
    return await service.list_mappings(pid=pid, status=status, department=department, page=page, page_size=page_size)


@router.get("/mappings/pids")
async def list_pids_for_department(
    department: str = Query(..., description="Department ID to filter by"),
    mongo: MongoDep = None,
) -> dict:
    """
    Return per-PID summary rows for a given department.

    Used by the operator UI department view to list all PIDs and their review status.

    Query params:
      department: Department ID (e.g. "214")

    Returns:
      {
        "department": str,
        "total": int,
        "pids": [
          {
            "pid": str,
            "total": int,
            "avg_confidence": float,
            "needs_review": bool,
            "confirmed": int,
            "rejected": int,
            "corrected": int,
          },
          ...
        ]
      }
    """
    db = mongo.get_db()

    # Step 1 — ground-truth PIDs come from tcin_records (populated by ingestion).
    # The departments dropdown is also driven by tcin_records, so this is the
    # authoritative source. mappings may not exist yet (pipeline not run).
    pids: list[str] = await db.tcin_records.distinct("pid", {"department_ids": department})
    if not pids:
        return {"department": department, "total": 0, "pids": []}

    # Step 2 — aggregate mapping stats per PID (only for PIDs that have been matched).
    stats_pipeline = [
        {"$match": {"pid": {"$in": pids}}},
        {
            "$group": {
                "_id": "$pid",
                "total": {"$sum": 1},
                "avg_confidence": {"$avg": "$color_confidence"},
                "confirmed": {"$sum": {"$cond": [{"$eq": ["$status", "CONFIRMED"]}, 1, 0]}},
                "rejected": {"$sum": {"$cond": [{"$eq": ["$status", "REJECTED"]}, 1, 0]}},
                "corrected": {"$sum": {"$cond": [{"$eq": ["$status", "CORRECTED"]}, 1, 0]}},
                "needs_review_count": {
                    "$sum": {
                        "$cond": [
                            {"$in": ["$status", ["NEEDS_REVIEW", "NO_MATCH", "NEEDS_SPOT_CHECK"]]},
                            1,
                            0,
                        ]
                    }
                },
            }
        },
    ]
    stats_by_pid: dict = {}
    async for doc in db.mappings.aggregate(stats_pipeline):
        stats_by_pid[doc["_id"]] = doc

    # Step 3 — build a row for every PID even if no mappings exist yet.
    rows = []
    for pid in pids:
        stat = stats_by_pid.get(pid, {})
        rows.append(
            {
                "pid": pid,
                "total": stat.get("total", 0),
                "avg_confidence": round(stat.get("avg_confidence") or 0.0, 4),
                "needs_review": stat.get("needs_review_count", 0) > 0,
                "confirmed": stat.get("confirmed", 0),
                "rejected": stat.get("rejected", 0),
                "corrected": stat.get("corrected", 0),
            }
        )

    # Sort worst-confidence-first (unmatched PIDs have 0.0 → float to top).
    rows.sort(key=lambda r: r["avg_confidence"])

    return {"department": department, "total": len(rows), "pids": rows}


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
    db = mongo.get_db()
    collection = db.mappings

    filter_query = {}
    if department:
        filter_query["department_ids"] = department

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
                "avg_confidence": {"$avg": "$color_confidence"},
                "high_conf": {"$sum": {"$cond": [{"$gte": ["$color_confidence", 0.8]}, 1, 0]}},
                "low_conf": {"$sum": {"$cond": [{"$lt": ["$color_confidence", 0.5]}, 1, 0]}},
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
    db = mongo.get_db()
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
