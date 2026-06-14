"""GET /api/v1/admin/stats — admin-only stats and metrics."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter

from plm_tcin_mapper_api.dependencies import MongoDep

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"])


@router.get("/admin/stats")
async def get_admin_stats(mongo: MongoDep = None) -> dict:
    """
    Get collection statistics for admin dashboard.

    Returns:
      {
        "mappings_count": int,
        "tcin_records_count": int,
        "variation_records_count": int,
        "feedback_count": int,
        "eval_runs_count": int,
        "llm_calls_count": int,
        "correction_impacts_count": int,
        "threshold_proposals_count": int,
        "alias_proposals_count": int,
        "timestamp": ISO datetime string
      }
    """
    db = mongo.get_db()

    async def _count(col_name: str) -> int:
        try:
            return await db[col_name].estimated_document_count()
        except Exception as exc:
            logger.error("admin/stats: failed to count collection '%s': %s", col_name, exc)
            return -1

    stats = {
        "mappings_count": await _count("mappings"),
        "tcin_records_count": await _count("tcin_records"),
        "variation_records_count": await _count("variation_records"),
        "feedback_count": await _count("feedback"),
        "eval_runs_count": await _count("extended_eval_runs"),
        "llm_calls_count": await _count("llm_calls"),
        "correction_impacts_count": await _count("correction_impacts"),
        "threshold_proposals_count": await _count("threshold_proposals"),
        "alias_proposals_count": await _count("alias_mining_proposals"),
        "timestamp": datetime.now(UTC).isoformat(),
    }

    logger.debug("admin/stats: %s", stats)
    return stats
