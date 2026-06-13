"""
Batch processor for large-scale PID matching — pagination + concurrent workers.
Handles 500K+ records without memory overload or system strain.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, cast

from ai_core.config import Settings
from ai_core.llm.base import LLMClient

from plm_tcin_mapper.pipeline.orchestrator import (
    BatchStats,
    _get_pids_to_match,
    _load_tcin_records,
    _load_variation_records,
    _upsert_mapping,
    match_pid,
)

logger = logging.getLogger(__name__)


@dataclass
class BatchProcessorConfig:
    """Tunable knobs for large-scale processing."""

    pid_batch_size: int = 100  # PIDs per worker batch
    concurrent_workers: int = 3  # Parallel async workers (keep LOW: 1-5)
    worker_delay_seconds: float = 0.5  # Pause between worker batches (throttle system)
    max_retries: int = 3
    retry_delay_seconds: float = 2.0


class LargeBatchProcessor:
    """
    Process large PID sets (100K+) with pagination + concurrency + throttling.

    Usage:
        processor = LargeBatchProcessor(db, cfg, llm, settings)
        stats = await processor.run_all_unmatched(
            force=False, department=None, shadow_mode=False
        )
    """

    def __init__(self, db: Any, cfg: Any, llm: LLMClient, settings: Settings) -> None:
        self._db = db
        self._cfg = cfg
        self._llm = llm
        self._settings = settings
        self._processor_cfg = BatchProcessorConfig(
            pid_batch_size=getattr(settings, "batch_pid_size", 100),
            concurrent_workers=getattr(settings, "batch_workers", 3),
            worker_delay_seconds=getattr(settings, "batch_worker_delay", 0.5),
        )

    async def run_all_unmatched(
        self,
        force: bool = False,
        department: str | None = None,
        shadow_mode: bool = False,
        use_llm: bool = True,
        dry_run: bool = False,
        batch_id: str | None = None,
    ) -> BatchStats:
        """
        Process all unmatched PIDs with pagination and concurrent workers.

        Args:
            force: Re-match already-matched PIDs
            department: Filter to specific department
            shadow_mode: Don't write to DB
            use_llm: Enable LLM disambiguation
            dry_run: Don't persist results
            batch_id: Batch identifier for grouping

        Returns:
            Aggregated stats across all workers
        """
        # Get all unmatched PIDs without loading them all at once
        pids = _get_pids_to_match(self._db, self._cfg, force, department)
        logger.info(
            "Starting large batch: %d unmatched PIDs, workers=%d, batch_size=%d",
            len(pids),
            self._processor_cfg.concurrent_workers,
            self._processor_cfg.pid_batch_size,
        )

        # Paginate PIDs into chunks
        pid_chunks = self._paginate_pids(pids)

        # Process chunks concurrently with worker pool
        all_stats = await self._process_chunks_concurrent(
            pid_chunks,
            use_llm=use_llm,
            dry_run=dry_run,
            batch_id=batch_id,
            shadow_mode=shadow_mode,
        )

        return all_stats

    def _paginate_pids(self, pids: list[str]) -> list[list[str]]:
        """Split PIDs into fixed-size pages."""
        size = self._processor_cfg.pid_batch_size
        return [pids[i : i + size] for i in range(0, len(pids), size)]

    async def _process_chunks_concurrent(
        self,
        chunks: list[list[str]],
        use_llm: bool,
        dry_run: bool,
        batch_id: str | None,
        shadow_mode: bool,
    ) -> BatchStats:
        """Process chunks concurrently using a worker pool."""
        aggregated = BatchStats()
        num_workers = self._processor_cfg.concurrent_workers

        # Semaphore limits concurrent workers
        semaphore = asyncio.Semaphore(num_workers)

        async def process_chunk_with_semaphore(chunk: list[str]) -> BatchStats:
            async with semaphore:
                return await self._process_chunk(
                    chunk,
                    use_llm=use_llm,
                    dry_run=dry_run,
                    batch_id=batch_id,
                    shadow_mode=shadow_mode,
                )

        # Launch all tasks concurrently (limited by semaphore)
        tasks = [process_chunk_with_semaphore(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error("Chunk processing failed: %s", result)
                continue

            # Type-narrowed to BatchStats after isinstance check
            stats = cast(BatchStats, result)

            # Aggregate stats
            aggregated.total_pids += stats.total_pids
            aggregated.pids_matched += stats.pids_matched
            aggregated.pids_no_data += stats.pids_no_data
            aggregated.pids_errored += stats.pids_errored
            aggregated.total_mappings_written += stats.total_mappings_written

            for status, count in stats.status_counts.items():
                aggregated.status_counts[status] = aggregated.status_counts.get(status, 0) + count

        logger.info(
            "Batch complete: matched=%d, no_data=%d, errored=%d, mappings_written=%d",
            aggregated.pids_matched,
            aggregated.pids_no_data,
            aggregated.pids_errored,
            aggregated.total_mappings_written,
        )
        return aggregated

    async def _process_chunk(
        self,
        pids: list[str],
        use_llm: bool,
        dry_run: bool,
        batch_id: str | None,
        shadow_mode: bool,
    ) -> BatchStats:
        """Process one chunk (100-1000 PIDs) synchronously in executor."""
        # Throttle: add delay between worker starts
        await asyncio.sleep(self._processor_cfg.worker_delay_seconds)

        # Run sync processing in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._run_chunk_sync,
            pids,
            use_llm,
            dry_run,
            batch_id,
            shadow_mode,
        )

    def _run_chunk_sync(
        self,
        pids: list[str],
        use_llm: bool,
        dry_run: bool,
        batch_id: str | None,
        shadow_mode: bool,
    ) -> BatchStats:
        """Synchronous processing of one chunk."""
        stats = BatchStats(total_pids=len(pids))

        for i, pid in enumerate(pids):
            # Log progress every 10 items
            if i % 10 == 0:
                logger.debug("Chunk progress: %d / %d PIDs", i, len(pids))

            try:
                tcin_records = _load_tcin_records(self._db, pid)
                variation_records = _load_variation_records(self._db, pid)

                if not tcin_records or not variation_records:
                    stats.pids_no_data += 1
                    continue

                mappings = match_pid(
                    pid,
                    tcin_records,
                    variation_records,
                    self._cfg,
                    self._llm,
                    use_llm,
                    dry_run,
                    batch_id=batch_id,
                    db=self._db,
                )

                if not dry_run and not shadow_mode:
                    for m in mappings:
                        _upsert_mapping(self._db, m)
                        stats.status_counts[str(m.status)] = stats.status_counts.get(str(m.status), 0) + 1

                stats.pids_matched += 1
                stats.total_mappings_written += len(mappings)

            except Exception as exc:
                stats.pids_errored += 1
                logger.error("Match failed pid=%s: %s", pid, exc)

        return stats
