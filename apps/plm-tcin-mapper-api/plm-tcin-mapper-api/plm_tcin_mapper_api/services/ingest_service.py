"""Ingestion service — runs the CSV ingestion pipeline via FastAPI."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from ai_core.config import Settings
from ai_mongo import MongoClientManager

from plm_tcin_mapper_api.models.schemas import IngestRequest, IngestResponse

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, mongo: MongoClientManager, settings: Settings) -> None:
        self._mongo = mongo
        self._settings = settings

    async def run(self, request: IngestRequest) -> IngestResponse:
        if request.async_mode:
            logger.info(
                "Ingestion accepted for background run: data_dir=%s chunk=%s dry_run=%s skip_existing=%s",
                request.data_dir,
                request.chunk,
                request.dry_run,
                request.skip_existing,
            )
            asyncio.create_task(self._run_in_background(request))  # noqa: RUF006
            return IngestResponse(
                status="accepted",
                chunks_processed=0,
                totals=self._empty_totals(),
                dry_run=request.dry_run,
                accepted=True,
                message="Ingestion started in background",
            )

        return await asyncio.get_event_loop().run_in_executor(None, self._run_sync, request)

    async def _run_in_background(self, request: IngestRequest) -> None:
        try:
            await asyncio.get_event_loop().run_in_executor(None, self._run_sync, request)
        except Exception:
            logger.exception("Background ingestion failed")

    @staticmethod
    def _empty_totals() -> dict[str, int]:
        return {
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "errored": 0,
        }

    def _run_sync(self, request: IngestRequest) -> IngestResponse:
        from plm_tcin_mapper_api.pipeline.ingestion import ingest_chunk

        cfg = self._settings
        data_dir = Path(request.data_dir or cfg.ingestion.data_dir)
        batch_size = request.batch_size or cfg.ingestion.batch_size

        logger.info(
            "Ingestion started: data_dir=%s chunk=%s batch_size=%s dry_run=%s skip_existing=%s",
            data_dir,
            request.chunk,
            batch_size,
            request.dry_run,
            request.skip_existing,
        )

        db = None if request.dry_run else self._mongo.get_sync_db()

        chunk_dirs = [data_dir / request.chunk] if request.chunk else [data_dir]

        for chunk_dir in chunk_dirs:
            if not chunk_dir.exists() or not chunk_dir.is_dir():
                raise FileNotFoundError(f"Chunk directory not found: {chunk_dir}")

            csv_files = list(chunk_dir.glob("*.csv"))
            if not csv_files:
                raise FileNotFoundError(
                    f"Invalid ingestion path: {chunk_dir}. Provide a chunk folder path containing CSV files (tcin.csv, variation.csv)."
                )

            lower_names = {p.name.lower() for p in csv_files}
            if "tcin.csv" not in lower_names or "variation.csv" not in lower_names:
                raise FileNotFoundError(f"Chunk folder must contain both tcin.csv and variation.csv: {chunk_dir}")

        from plm_tcin_mapper_api.pipeline.ingestion import IngestStats

        total = IngestStats()
        for idx, chunk_dir in enumerate(chunk_dirs, start=1):
            logger.info("Ingesting chunk %s/%s: %s", idx, len(chunk_dirs), chunk_dir)
            file_stats = ingest_chunk(
                chunk_dir=chunk_dir,
                db=db,
                batch_size=batch_size,
                skip_existing=request.skip_existing,
                dry_run=request.dry_run,
            )
            total.chunks_processed += 1
            total.file_stats.extend(file_stats)

            chunk_inserted = sum(s.inserted for s in file_stats)
            chunk_updated = sum(s.updated for s in file_stats)
            chunk_skipped = sum(s.skipped for s in file_stats)
            chunk_errored = sum(s.errored for s in file_stats)
            logger.info(
                "Chunk complete: %s inserted=%s updated=%s skipped=%s errored=%s",
                chunk_dir.name,
                chunk_inserted,
                chunk_updated,
                chunk_skipped,
                chunk_errored,
            )

        logger.info(
            "Ingestion finished: chunks_processed=%s totals=%s",
            total.chunks_processed,
            total.totals,
        )

        return IngestResponse(
            status="ok",
            chunks_processed=total.chunks_processed,
            totals=total.totals,
            dry_run=request.dry_run,
        )
