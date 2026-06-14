"""CLI tool for large-scale batch processing (500K+ PIDs)."""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime

import typer
from ai_core.config import get_settings
from ai_core.logging import setup_logging
from ai_mongo import MongoClientManager

from plm_tcin_mapper_api.dependencies import get_llm_client
from plm_tcin_mapper_api.pipeline.batch_processor import LargeBatchProcessor

app = typer.Typer(help="Run large-scale TCIN matching batches with throttling and concurrency control.")

logger = logging.getLogger(__name__)


@app.command()
def match_all_unmatched(
    department: str | None = typer.Option(
        None,
        "--department",
        "-d",
        help="Filter to specific department (optional)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Re-match already-matched PIDs",
    ),
    shadow_mode: bool = typer.Option(
        False,
        "--shadow",
        "-s",
        help="Preview mode: don't write to DB",
    ),
    use_llm: bool = typer.Option(
        True,
        "--llm/--no-llm",
        help="Enable LLM disambiguation",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Don't persist mappings (analyze only)",
    ),
    workers: int = typer.Option(
        None,
        "--workers",
        "-w",
        help="Override concurrent workers (1-10)",
    ),
    batch_size: int = typer.Option(
        None,
        "--batch-size",
        "-b",
        help="Override PIDs per batch (10-1000)",
    ),
) -> None:
    """
    Process all unmatched PIDs with concurrent workers and throttling.

    Example:
        python -m plm_tcin_mapper.cli.batch_runner match-all-unmatched --workers 3 --batch-size 100
    """
    setup_logging()
    settings = get_settings()

    logger.info("=" * 80)
    logger.info("Starting large batch matcher")
    logger.info("  Department: %s", department or "all")
    logger.info("  Force re-match: %s", force)
    logger.info("  Shadow mode (no DB writes): %s", shadow_mode)
    logger.info("  Use LLM: %s", use_llm)
    logger.info("  Dry run: %s", dry_run)
    logger.info("=" * 80)

    try:
        # Initialize dependencies
        mongo_mgr = MongoClientManager(settings.mongo.url, settings.mongo.database)
        db = mongo_mgr.get_sync_db()
        llm = get_llm_client()

        # Create processor with optional overrides
        processor = LargeBatchProcessor(db, settings, llm, settings)

        # Override config if provided
        if workers:
            if not 1 <= workers <= 10:
                raise ValueError("--workers must be 1-10")
            processor._processor_cfg.concurrent_workers = workers
            logger.info("Overridden workers: %d", workers)

        if batch_size:
            if not 10 <= batch_size <= 1000:
                raise ValueError("--batch-size must be 10-1000")
            processor._processor_cfg.pid_batch_size = batch_size
            logger.info("Overridden batch size: %d", batch_size)

        # Run the batch
        start_time = datetime.now()
        stats = asyncio.run(
            processor.run_all_unmatched(
                force=force,
                department=department,
                shadow_mode=shadow_mode,
                use_llm=use_llm,
                dry_run=dry_run,
            )
        )
        elapsed = (datetime.now() - start_time).total_seconds()

        # Print results
        logger.info("=" * 80)
        logger.info("Batch complete in %.1f seconds", elapsed)
        logger.info("  Total PIDs: %d", stats.total_pids)
        logger.info("  Matched: %d", stats.pids_matched)
        logger.info("  No data: %d", stats.pids_no_data)
        logger.info("  Errored: %d", stats.pids_errored)
        logger.info("  Mappings written: %d", stats.total_mappings_written)
        logger.info("  Status breakdown: %s", stats.status_counts)
        logger.info("  Throughput: %.1f PIDs/sec", stats.total_pids / elapsed if elapsed > 0 else 0)
        logger.info("=" * 80)

        sys.exit(0 if stats.pids_errored == 0 else 1)

    except Exception as e:
        logger.error("Batch failed: %s", e, exc_info=True)
        sys.exit(2)


@app.command()
def status() -> None:
    """Show batch processing configuration."""
    setup_logging()
    settings = get_settings()

    batch_cfg = getattr(settings, "batch_processing", {})
    typer.echo("\nBatch Processing Configuration:")
    typer.echo(f"  PID batch size: {batch_cfg.get('pid_batch_size', 100)}")
    typer.echo(f"  Concurrent workers: {batch_cfg.get('concurrent_workers', 3)}")
    typer.echo(f"  Worker delay (sec): {batch_cfg.get('worker_delay_seconds', 0.5)}")
    typer.echo(f"  Large batch threshold: {batch_cfg.get('large_batch_threshold', 1000)}")
    typer.echo()


if __name__ == "__main__":
    app()
