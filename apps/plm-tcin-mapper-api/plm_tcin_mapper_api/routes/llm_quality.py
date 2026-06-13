"""GET /api/v1/llm/quality — fetch LLM call quality metrics."""

from __future__ import annotations

from fastapi import APIRouter

from plm_tcin_mapper_api.dependencies import MongoDep

router = APIRouter(tags=["llm"])


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
    db = await mongo.get_db()
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

    # Get recent calls
    recent = (
        await collection.find({}).sort("_id", -1).limit(20).to_list(20)
    )
    # Convert ObjectIds to strings for JSON serialization
    recent = [
        {
            **call,
            "_id": str(call.get("_id", "")),
            "timestamp": str(call.get("timestamp", "")),
        }
        for call in recent
    ]

    return {
        "total_calls": total_calls,
        "error_count": error_calls,
        "error_rate": error_calls / total_calls if total_calls > 0 else 0,
        "avg_tokens_used": metric.get("avg_tokens", 0),
        "avg_latency_ms": metric.get("avg_latency", 0),
        "recent_calls": recent,
    }
