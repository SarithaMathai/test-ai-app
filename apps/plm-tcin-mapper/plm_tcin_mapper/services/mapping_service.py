"""Mapping service — wraps the matching pipeline for use by FastAPI routes."""

from __future__ import annotations

import asyncio
from uuid import uuid4

from ai_core.config import Settings
from ai_core.llm.base import LLMClient
from ai_mongo import MongoClientManager

from plm_tcin_mapper.models.schemas import (
    MappingItem,
    MappingRunRequest,
    MappingRunResponse,
    MappingsResponse,
)

# Collection name constants
_TCIN_COL = "tcin_records"
_VAR_COL = "variation_records"
_MAPPING_COL = "mappings"


class MappingService:
    def __init__(self, mongo: MongoClientManager, llm: LLMClient, settings: Settings) -> None:
        self._mongo = mongo
        self._llm = llm
        self._settings = settings

    async def run(self, request: MappingRunRequest) -> MappingRunResponse:
        """Run the matching pipeline. Executes sync pipeline in a thread pool to avoid blocking."""
        return await asyncio.get_event_loop().run_in_executor(None, self._run_sync, request)

    def _run_sync(self, request: MappingRunRequest) -> MappingRunResponse:
        from plm_tcin_mapper.pipeline.orchestrator import _get_pids_to_match, run_batch

        db = self._mongo.get_sync_db()
        cfg = self._settings

        batch_id = request.batch_id or (
            f"shadow_{uuid4().hex[:8]}" if request.shadow else f"batch_{uuid4().hex[:8]}"
        )

        pids = [request.pid] if request.pid else _get_pids_to_match(db, cfg, request.force, request.department)

        stats = run_batch(
            pids=pids,
            db=db,
            cfg=cfg,
            llm=self._llm,
            use_llm=request.use_llm,
            dry_run=request.dry_run,
            batch_id=batch_id,
            shadow_mode=request.shadow,
        )

        return MappingRunResponse(
            status="ok",
            batch_id=batch_id,
            total_pids=stats.total_pids,
            pids_matched=stats.pids_matched,
            pids_no_data=stats.pids_no_data,
            pids_errored=stats.pids_errored,
            total_mappings_written=stats.total_mappings_written,
            status_counts={str(k): v for k, v in stats.status_counts.items()},
            dry_run=request.dry_run,
        )

    async def list_mappings(
        self,
        pid: str | None,
        status: str | None,
        department: str | None,
        page: int,
        page_size: int,
    ) -> MappingsResponse:
        db = self._mongo.get_db()
        col = db[_MAPPING_COL]

        filt: dict = {}
        if pid:
            filt["pid"] = pid
        if status:
            filt["status"] = status
        if department:
            filt["department_ids"] = department

        total = await col.count_documents(filt)
        skip = (page - 1) * page_size
        docs = await col.find(filt).skip(skip).limit(page_size).to_list(page_size)

        items = [
            MappingItem(
                id=str(doc.get("_id", "")),
                pid=doc["pid"],
                tcin_id=doc["tcin_id"],
                tcin_color=doc.get("tcin_color", ""),
                tcin_color_name=doc.get("tcin_color_name", ""),
                tcin_size=doc.get("tcin_size", ""),
                matched_impression_name=doc.get("matched_impression_name"),
                matched_impression_id=doc.get("matched_impression_id"),
                color_confidence=doc.get("color_confidence", 0.0),
                confidence_tier=doc.get("confidence_tier", "LOW"),
                status=doc.get("status", "NEEDS_REVIEW"),
                match_round=doc.get("match_round"),
                batch_id=doc.get("batch_id"),
            )
            for doc in docs
        ]
        return MappingsResponse(total=total, page=page, page_size=page_size, items=items)
