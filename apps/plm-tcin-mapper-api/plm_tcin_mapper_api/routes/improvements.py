"""GET/POST /api/v1/improvements — correction impact tracking."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Body

from plm_tcin_mapper_api.dependencies import MongoDep

router = APIRouter(tags=["improvements"])


@router.get("/improvements")
async def list_improvements(mongo: MongoDep = None, limit: int = 100, skip: int = 0) -> dict:
    """
    List recent correction impact records.

    Query params:
      limit: Max number of records (default 100)
      skip: Number of records to skip (default 0)

    Returns:
      {
        "total": int,
        "improvements": [list of correction impact records]
      }
    """
    db = await mongo.get_db()
    collection = db.correction_impacts

    total = await collection.count_documents({})
    records = (
        await collection.find({})
        .sort("_id", -1)
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )

    # Serialize ObjectIds
    records = [
        {
            **record,
            "_id": str(record.get("_id", "")),
            "timestamp": str(record.get("timestamp", "")),
        }
        for record in records
    ]

    return {"total": total, "improvements": records}


@router.post("/improvements")
async def create_improvement(
    mongo: MongoDep = None,
    impact: dict = Body(...),
) -> dict:
    """
    Record a new correction impact entry.

    Request body:
      {
        "pid": str,
        "original_mapping": str,
        "corrected_mapping": str,
        "reason": str,
        "impact_estimate": float (0-1)
      }

    Returns:
      {
        "id": ObjectId (as string),
        "status": "created"
      }
    """
    db = await mongo.get_db()
    collection = db.correction_impacts

    doc = {
        **impact,
        "timestamp": datetime.utcnow(),
    }

    result = await collection.insert_one(doc)
    return {"id": str(result.inserted_id), "status": "created"}
