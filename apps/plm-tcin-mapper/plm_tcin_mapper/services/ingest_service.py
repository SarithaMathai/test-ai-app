"""Ingestion service — runs the CSV ingestion pipeline via FastAPI."""

from __future__ import annotations

import asyncio

from ai_core.config import Settings
from ai_mongo import MongoClientManager

from plm_tcin_mapper.models.schemas import IngestRequest, IngestResponse


class IngestionService:
    def __init__(self, mongo: MongoClientManager, settings: Settings) -> None:
        self._mongo = mongo
        self._settings = settings

    async def run(self, request: IngestRequest) -> IngestResponse:
        return await asyncio.get_event_loop().run_in_executor(None, self._run_sync, request)

    def _run_sync(self, request: IngestRequest) -> IngestResponse:
        from pathlib import Path

        from plm_tcin_mapper.pipeline.ingestion import ingest_chunk

        cfg = self._settings
        data_dir = Path(request.data_dir or cfg.ingestion.data_dir)
        batch_size = request.batch_size or cfg.ingestion.batch_size

        db = None if request.dry_run else self._mongo.get_sync_db()

        if request.chunk:
            chunk_dirs = [data_dir / request.chunk]
        else:
            chunk_dirs = sorted(d for d in data_dir.iterdir() if d.is_dir() and d.name.startswith("chunk_"))

        from plm_tcin_mapper.pipeline.ingestion import IngestStats

        total = IngestStats()
        for chunk_dir in chunk_dirs:
            file_stats = ingest_chunk(
                chunk_dir=chunk_dir,
                db=db,
                batch_size=batch_size,
                skip_existing=request.skip_existing,
                dry_run=request.dry_run,
            )
            total.chunks_processed += 1
            total.file_stats.extend(file_stats)

        return IngestResponse(
            status="ok",
            chunks_processed=total.chunks_processed,
            totals=total.totals,
            dry_run=request.dry_run,
        )
