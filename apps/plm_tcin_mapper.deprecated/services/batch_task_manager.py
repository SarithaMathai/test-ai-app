"""Background task manager for large-scale batch processing in the cloud."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ai_core.config import Settings
from ai_core.llm.base import LLMClient
from ai_mongo import MongoClientManager

from plm_tcin_mapper.pipeline.batch_processor import LargeBatchProcessor

logger = logging.getLogger(__name__)


@dataclass
class BatchJobStatus:
    """Tracks status of a background batch job."""

    batch_id: str
    department: str | None
    status: str  # "queued" | "running" | "completed" | "failed"
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_pids: int = 0
    pids_matched: int = 0
    pids_no_data: int = 0
    pids_errored: int = 0
    total_mappings_written: int = 0
    status_counts: dict[str, int] = field(default_factory=dict)
    error_message: str | None = None
    config: dict[str, Any] = field(default_factory=dict)  # Store workers, batch_size, etc.


class BatchTaskManager:
    """
    Fire-and-forget background task manager for large batch processing.

    Stores job status in memory (simple). For multi-instance deployments,
    consider storing in MongoDB or Redis.
    """

    def __init__(self) -> None:
        # In-memory job registry: batch_id -> BatchJobStatus
        self._jobs: dict[str, BatchJobStatus] = {}
        self._lock = asyncio.Lock()

    async def start_batch_job(
        self,
        mongo: MongoClientManager,
        settings: Settings,
        llm: LLMClient,
        department: str | None = None,
        workers: int = 3,
        batch_size: int = 100,
        use_llm: bool = True,
        force: bool = False,
        shadow_mode: bool = False,
        dry_run: bool = False,
    ) -> str:
        """
        Start a background batch job. Returns immediately with batch_id.

        Args:
            department: Filter to specific department (optional)
            workers: Concurrent workers (1-10)
            batch_size: PIDs per batch (10-1000)
            use_llm: Enable LLM disambiguation
            force: Re-match already-matched PIDs
            shadow_mode: Don't write to DB
            dry_run: Don't persist mappings

        Returns:
            batch_id for tracking progress
        """
        batch_id = f"batch_{uuid.uuid4().hex[:8]}"

        # Create job record
        job = BatchJobStatus(
            batch_id=batch_id,
            department=department,
            status="queued",
            config={
                "workers": workers,
                "batch_size": batch_size,
                "use_llm": use_llm,
                "force": force,
                "shadow_mode": shadow_mode,
                "dry_run": dry_run,
            },
        )

        async with self._lock:
            self._jobs[batch_id] = job

        logger.info(
            "Batch job queued: %s (department=%s, workers=%d, batch_size=%d)",
            batch_id,
            department,
            workers,
            batch_size,
        )

        # Fire background task (don't await) — intentional fire-and-forget pattern
        asyncio.create_task(  # noqa: RUF006 — intentional, not cancelling
            self._run_batch_job(
                batch_id=batch_id,
                mongo=mongo,
                settings=settings,
                llm=llm,
                department=department,
                workers=workers,
                batch_size=batch_size,
                use_llm=use_llm,
                force=force,
                shadow_mode=shadow_mode,
                dry_run=dry_run,
            )
        )

        return batch_id

    async def _run_batch_job(
        self,
        batch_id: str,
        mongo: MongoClientManager,
        settings: Settings,
        llm: LLMClient,
        department: str | None,
        workers: int,
        batch_size: int,
        use_llm: bool,
        force: bool,
        shadow_mode: bool,
        dry_run: bool,
    ) -> None:
        """Run the batch job in the background."""
        try:
            # Update status to running
            async with self._lock:
                job = self._jobs[batch_id]
                job.status = "running"
                job.started_at = datetime.utcnow()

            logger.info("Batch job started: %s", batch_id)

            # Get database connection (sync)
            db = mongo.get_sync_db()

            # Create processor
            processor = LargeBatchProcessor(db, settings, llm, settings)

            # Override config
            processor._processor_cfg.concurrent_workers = min(max(workers, 1), 10)
            processor._processor_cfg.pid_batch_size = min(max(batch_size, 10), 1000)

            # Log config
            logger.info(
                "Batch job config: workers=%d, batch_size=%d, use_llm=%s, force=%s",
                processor._processor_cfg.concurrent_workers,
                processor._processor_cfg.pid_batch_size,
                use_llm,
                force,
            )

            # Run the batch (runs in executor to not block)
            stats = await processor.run_all_unmatched(
                force=force,
                department=department,
                shadow_mode=shadow_mode,
                use_llm=use_llm,
                dry_run=dry_run,
                batch_id=batch_id,
            )

            # Update job with results
            async with self._lock:
                job = self._jobs[batch_id]
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                job.total_pids = stats.total_pids
                job.pids_matched = stats.pids_matched
                job.pids_no_data = stats.pids_no_data
                job.pids_errored = stats.pids_errored
                job.total_mappings_written = stats.total_mappings_written
                job.status_counts = stats.status_counts

            if job.started_at and job.completed_at:
                elapsed = (job.completed_at - job.started_at).total_seconds()
            else:
                elapsed = 0.0

            logger.info(
                "Batch job completed: %s in %.1f seconds. Matched=%d, errors=%d, mappings=%d",
                batch_id,
                elapsed,
                stats.pids_matched,
                stats.pids_errored,
                stats.total_mappings_written,
            )

        except Exception as e:
            logger.error("Batch job failed: %s - %s", batch_id, e, exc_info=True)

            async with self._lock:
                if batch_id in self._jobs:
                    job = self._jobs[batch_id]
                    job.status = "failed"
                    job.completed_at = datetime.utcnow()
                    job.error_message = str(e)

    async def get_job_status(self, batch_id: str) -> BatchJobStatus | None:
        """Get the current status of a batch job."""
        async with self._lock:
            return self._jobs.get(batch_id)

    async def list_jobs(self, status: str | None = None) -> list[BatchJobStatus]:
        """List all batch jobs, optionally filtered by status."""
        async with self._lock:
            jobs = list(self._jobs.values())
            if status:
                jobs = [j for j in jobs if j.status == status]
            return sorted(jobs, key=lambda j: j.created_at, reverse=True)


# Global singleton
_batch_manager: BatchTaskManager | None = None


def get_batch_task_manager() -> BatchTaskManager:
    """Get or create the global batch task manager."""
    global _batch_manager
    if _batch_manager is None:
        _batch_manager = BatchTaskManager()
    return _batch_manager
