"""GET /api/v1/admin/stats — admin-only stats and metrics."""

from __future__ import annotations

from fastapi import APIRouter

from plm_tcin_mapper_api.dependencies import MongoDep

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
    db = await mongo.get_db()

    stats = {
        "mappings_count": await db.mappings.estimated_document_count(),
        "tcin_records_count": await db.tcin_records.estimated_document_count(),
        "variation_records_count": await db.variation_records.estimated_document_count(),
        "feedback_count": await db.feedback.estimated_document_count(),
        "eval_runs_count": await db.extended_eval_runs.estimated_document_count(),
        "llm_calls_count": await db.llm_calls.estimated_document_count(),
        "correction_impacts_count": await db.correction_impacts.estimated_document_count(),
        "threshold_proposals_count": await db.threshold_proposals.estimated_document_count(),
        "alias_proposals_count": await db.alias_mining_proposals.estimated_document_count(),
    }

    return stats
