"""GET /api/v1/llm/quality — fetch LLM call quality metrics."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from bson import ObjectId
from fastapi import APIRouter

from plm_tcin_mapper_api.dependencies import MongoDep

logger = logging.getLogger(__name__)
router = APIRouter(tags=["llm"])


def _serialize_doc(doc: dict) -> dict[str, Any]:
    """Convert BSON-specific types to JSON-safe Python types."""
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


@router.get("/llm/quality")
async def get_llm_quality(mongo: MongoDep = None) -> dict:
    """
    Get aggregate LLM call quality metrics.

    Returns:
      {
        "total_calls": int,
        "avg_tokens_used": float,
        "avg_latency_ms": float,
        "error_rate": float,
        "recent_calls": [list of recent call records]
      }
    """
    db = mongo.get_db()
    collection = db.llm_calls

    # Get basic counts
    total_calls = await collection.count_documents({})
    error_calls = await collection.count_documents({"status": "error"})

    # Get aggregation metrics
    pipeline = [
        {
            "$group": {
                "_id": None,
                "avg_tokens": {"$avg": {"$add": ["$tokens_used.prompt", "$tokens_used.completion"]}},
                "avg_latency": {"$avg": "$latency_ms"},
            }
        }
    ]
    metrics = await collection.aggregate(pipeline).to_list(1)
    metric = metrics[0] if metrics else {"avg_tokens": 0, "avg_latency": 0}

    # Get recent calls — fully serialize all BSON types
    raw_recent = await collection.find({}).sort("_id", -1).limit(20).to_list(20)
    recent = [_serialize_doc(call) for call in raw_recent]

    logger.debug("llm/quality: total_calls=%d error_calls=%d", total_calls, error_calls)
    return {
        "total_calls": total_calls,
        "error_count": error_calls,
        "error_rate": error_calls / total_calls if total_calls > 0 else 0,
        "avg_tokens_used": metric.get("avg_tokens") or 0,
        "avg_latency_ms": metric.get("avg_latency") or 0,
        "recent_calls": recent,
    }
