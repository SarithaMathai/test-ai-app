"""GET/POST /api/v1/improvements — correction impact tracking."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Body

from plm_tcin_mapper_api.dependencies import MongoDep

logger = logging.getLogger(__name__)
router = APIRouter(tags=["improvements"])


def _serialize_doc(doc: dict) -> dict[str, Any]:
    """Convert any BSON-specific types to JSON-safe Python types."""
    out: dict[str, Any] = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = _serialize_doc(v)
        elif isinstance(v, list):
            out[k] = [
                _serialize_doc(i) if isinstance(i, dict) else (str(i) if isinstance(i, ObjectId) else i) for i in v
            ]
        else:
            out[k] = v
    return out


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
    db = mongo.get_db()
    collection = db.correction_impacts

    safe_limit = max(1, min(limit, 1000))
    total = await collection.count_documents({})
    raw_records = await collection.find({}).sort("_id", -1).skip(skip).limit(safe_limit).to_list(safe_limit)

    records = [_serialize_doc(r) for r in raw_records]
    logger.debug("list_improvements: total=%d returned=%d", total, len(records))
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
    db = mongo.get_db()
    collection = db.correction_impacts

    doc = {
        **impact,
        "timestamp": datetime.utcnow(),
    }

    result = await collection.insert_one(doc)
    logger.info("create_improvement: inserted _id=%s", result.inserted_id)
    return {"id": str(result.inserted_id), "status": "created"}
