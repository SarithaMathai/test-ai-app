"""Routes for large-scale batch processing (fire-and-forget)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from plm_tcin_mapper.dependencies import (
    BatchTaskManagerDep,
    get_app_settings,
    get_llm_client,
    get_mongo,
)
from plm_tcin_mapper.models.schemas import (
    BatchJobListResponse,
    BatchJobStatusResponse,
    LargeBatchRequest,
    LargeBatchResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["batch-processing"], prefix="/batch")


@router.post("/start", response_model=LargeBatchResponse)
async def start_large_batch(
    request: LargeBatchRequest,
    task_manager: BatchTaskManagerDep,
) -> LargeBatchResponse:
    """
    Start a large-scale background batch processing job (fire-and-forget).

    Returns immediately with a batch_id for tracking progress.
    The actual processing happens asynchronously in the background.

    Args:
        department: (optional) Filter to specific department
        workers: Concurrent workers (1-10, default 3)
        batch_size: PIDs per batch chunk (10-1000, default 100)
        use_llm: Enable LLM disambiguation (default True)
        force: Re-match already-matched PIDs (default False)
        shadow_mode: Preview mode - don't write to DB (default False)
        dry_run: Don't persist mappings (default False)

    Example:
        POST /api/v1/batch/start
        {
            "department": "MENS_APPAREL",
            "workers": 3,
            "batch_size": 100
        }

        Response:
        {
            "status": "queued",
            "batch_id": "batch_a1b2c3d4",
            "department": "MENS_APPAREL",
            "message": "Batch job queued successfully",
            "config": {
                "workers": 3,
                "batch_size": 100,
                "use_llm": true,
                ...
            }
        }
    """
    # Validate inputs
    if not 1 <= request.workers <= 10:
        raise HTTPException(status_code=400, detail="workers must be 1-10")
    if not 10 <= request.batch_size <= 1000:
        raise HTTPException(status_code=400, detail="batch_size must be 10-1000")

    # Get dependencies
    mongo = get_mongo()
    settings = get_app_settings()
    llm = get_llm_client()

    # Start background job
    batch_id = await task_manager.start_batch_job(
        mongo=mongo,
        settings=settings,
        llm=llm,
        department=request.department,
        workers=request.workers,
        batch_size=request.batch_size,
        use_llm=request.use_llm,
        force=request.force,
        shadow_mode=request.shadow_mode,
        dry_run=request.dry_run,
    )

    logger.info(
        "Large batch job started: batch_id=%s, department=%s, workers=%d",
        batch_id,
        request.department or "all",
        request.workers,
    )

    return LargeBatchResponse(
        status="queued",
        batch_id=batch_id,
        department=request.department,
        message=f"Batch job {batch_id} queued successfully. Use /batch/status/{batch_id} to track progress.",
        config={
            "workers": request.workers,
            "batch_size": request.batch_size,
            "use_llm": request.use_llm,
            "force": request.force,
            "shadow_mode": request.shadow_mode,
            "dry_run": request.dry_run,
        },
    )


@router.get("/status/{batch_id}", response_model=BatchJobStatusResponse)
async def get_batch_status(
    batch_id: str,
    task_manager: BatchTaskManagerDep,
) -> BatchJobStatusResponse:
    """
    Get the status of a batch job.

    Args:
        batch_id: The batch job ID returned by /batch/start

    Returns:
        Job status including progress, errors, and results

    Example:
        GET /api/v1/batch/status/batch_a1b2c3d4

        Response (while running):
        {
            "batch_id": "batch_a1b2c3d4",
            "status": "running",
            "created_at": "2026-06-12T10:30:00",
            "started_at": "2026-06-12T10:30:05",
            "total_pids": 500000,
            "pids_matched": 123456,
            "pids_no_data": 100,
            "pids_errored": 50,
            ...
        }

        Response (completed):
        {
            "batch_id": "batch_a1b2c3d4",
            "status": "completed",
            "created_at": "2026-06-12T10:30:00",
            "started_at": "2026-06-12T10:30:05",
            "completed_at": "2026-06-12T20:15:30",
            "total_pids": 500000,
            "pids_matched": 498765,
            "pids_no_data": 1000,
            "pids_errored": 235,
            "elapsed_seconds": 34785.0,
            "throughput_pids_per_sec": 14.37,
            ...
        }
    """
    job = await task_manager.get_job_status(batch_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Batch job {batch_id} not found")

    # Compute elapsed time and throughput
    elapsed_seconds = None
    throughput_pids_per_sec = None

    if job.started_at and job.completed_at:
        elapsed_seconds = (job.completed_at - job.started_at).total_seconds()
        if elapsed_seconds > 0 and job.total_pids > 0:
            throughput_pids_per_sec = job.total_pids / elapsed_seconds

    return BatchJobStatusResponse(
        batch_id=job.batch_id,
        department=job.department,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        total_pids=job.total_pids,
        pids_matched=job.pids_matched,
        pids_no_data=job.pids_no_data,
        pids_errored=job.pids_errored,
        total_mappings_written=job.total_mappings_written,
        status_counts=job.status_counts,
        error_message=job.error_message,
        config=job.config,
        elapsed_seconds=elapsed_seconds,
        throughput_pids_per_sec=throughput_pids_per_sec,
    )


@router.get("/list", response_model=BatchJobListResponse)
async def list_batch_jobs(
    task_manager: BatchTaskManagerDep,
    status: str | None = Query(None, description="Filter by status: queued, running, completed, failed"),
) -> BatchJobListResponse:
    """
    List all batch jobs, optionally filtered by status.

    Args:
        status: (optional) Filter to: queued, running, completed, or failed

    Returns:
        List of batch jobs with their current status

    Example:
        GET /api/v1/batch/list?status=running

        Response:
        {
            "total": 3,
            "jobs": [
                {
                    "batch_id": "batch_a1b2c3d4",
                    "status": "running",
                    "created_at": "2026-06-12T10:30:00",
                    ...
                },
                ...
            ]
        }
    """
    jobs = await task_manager.list_jobs(status=status)

    job_responses = []
    for job in jobs:
        # Compute elapsed time and throughput
        elapsed_seconds = None
        throughput_pids_per_sec = None

        if job.started_at and job.completed_at:
            elapsed_seconds = (job.completed_at - job.started_at).total_seconds()
            if elapsed_seconds > 0 and job.total_pids > 0:
                throughput_pids_per_sec = job.total_pids / elapsed_seconds

        job_responses.append(
            BatchJobStatusResponse(
                batch_id=job.batch_id,
                department=job.department,
                status=job.status,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                total_pids=job.total_pids,
                pids_matched=job.pids_matched,
                pids_no_data=job.pids_no_data,
                pids_errored=job.pids_errored,
                total_mappings_written=job.total_mappings_written,
                status_counts=job.status_counts,
                error_message=job.error_message,
                config=job.config,
                elapsed_seconds=elapsed_seconds,
                throughput_pids_per_sec=throughput_pids_per_sec,
            )
        )

    return BatchJobListResponse(
        total=len(job_responses),
        jobs=job_responses,
    )
