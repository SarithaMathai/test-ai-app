"""Pydantic request/response schemas for the TCIN Mapper API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

# ── Ingest ────────────────────────────────────────────────────────────────────


class IngestRequest(BaseModel):
    data_dir: str | None = None
    batch_size: int | None = None
    skip_existing: bool = True
    dry_run: bool = False
    chunk: str | None = None
    async_mode: bool = False


class IngestResponse(BaseModel):
    status: str
    chunks_processed: int
    totals: dict[str, int]
    dry_run: bool
    accepted: bool = False
    message: str | None = None


# ── Mapping run ───────────────────────────────────────────────────────────────


class MappingRunRequest(BaseModel):
    pid: str | None = None
    department: str | None = None
    # unmatched_only=False (default) → process ALL PIDs in scope (re-runs already matched).
    # unmatched_only=True           → skip PIDs that already have a non-NO_MATCH mapping.
    unmatched_only: bool = False
    force: bool = False  # kept for backward-compat; equivalent to not unmatched_only
    use_llm: bool = True
    dry_run: bool = False
    shadow: bool = False
    batch_id: str | None = None


class MappingRunResponse(BaseModel):
    status: str
    batch_id: str
    total_pids: int
    pids_matched: int
    pids_no_data: int
    pids_errored: int
    total_mappings_written: int
    status_counts: dict[str, int]
    dry_run: bool


# ── Mappings query ────────────────────────────────────────────────────────────


class ColorCandidateItem(BaseModel):
    impression_name: str
    score: float
    reason: str = ""


class MappingItem(BaseModel):
    id: str
    pid: str
    tcin_id: str
    tcin_color: str
    tcin_color_name: str
    tcin_size: str
    matched_impression_name: str | None
    matched_impression_id: str | None
    color_confidence: float
    confidence_tier: str
    status: str
    match_round: str | None
    batch_id: str | None
    # enriched fields — used by the operator UI
    department_ids: list[str] = []
    variation_size: str | None = None
    color_match_reason: str | None = None
    color_possible_values: list[ColorCandidateItem] = []
    llm_rationale: str | None = None


class MappingsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[MappingItem]


# ── Feedback ──────────────────────────────────────────────────────────────────


class FeedbackRequest(BaseModel):
    mapping_id: str
    pid: str
    tcin_id: str
    action: str  # CONFIRM | REJECT | CORRECT
    reviewer: str | None = None
    notes: str | None = None
    suggested_impression_id: str | None = None
    suggested_impression_name: str | None = None


class FeedbackResponse(BaseModel):
    status: str
    feedback_id: str


# ── Eval ──────────────────────────────────────────────────────────────────────


class EvalResponse(BaseModel):
    id: str
    total_mappings: int
    by_status: dict[str, int]
    by_tier: dict[str, int]
    pct_high: float
    pct_good: float
    pct_fair: float
    pct_low: float
    avg_color_confidence: float
    correction_rate: float
    guardrail_alerts: list[str]


# ── Extended Evaluation ───────────────────────────────────────────────────


class SignalAccuracyItem(BaseModel):
    signal_type: str
    occurrences: int
    corrections: int
    correction_rate: float
    avg_confidence: float
    confidence_by_tier: dict[str, int]


class DepartmentMetricsItem(BaseModel):
    department: str
    total_mappings: int
    pct_high_confidence: float
    correction_rate: float
    avg_confidence: float
    by_match_round: dict[str, int]


class LLMImpactItem(BaseModel):
    total_llm_calls: int
    llm_corrected: int
    llm_correction_rate: float
    llm_avg_confidence: float
    deterministic_corrected: int
    deterministic_correction_rate: float
    llm_vs_deterministic_improvement: float


class ExtendedEvalResponse(BaseModel):
    id: str
    total_mappings: int
    by_status: dict[str, int]
    by_tier: dict[str, int]
    pct_high: float
    pct_good: float
    pct_fair: float
    pct_low: float
    avg_color_confidence: float
    correction_rate: float
    per_signal_accuracy: dict[str, SignalAccuracyItem]
    per_department_metrics: list[DepartmentMetricsItem]
    llm_impact: LLMImpactItem | None
    confidence_calibration_error: float
    high_confidence_actual_correction_rate: float
    low_confidence_actual_correction_rate: float
    guardrail_alerts: list[str]


# ── Health ────────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str
    llm_provider: str
    llm_model: str
    mongo_ok: bool


# ── Alias Mining ──────────────────────────────────────────────────────────


class AliasMiningProposalItem(BaseModel):
    id: str
    proposal_type: str
    status: str
    base_color: str
    keyword: str
    suggested_base_color: str | None = None
    frequency: int
    confidence: float
    rationale: str
    estimated_impact: str | None = None
    created_at: str


class AliasMiningAnalyzeRequest(BaseModel):
    min_frequency: int = 3
    min_confidence: float = 0.60
    limit: int | None = None


class AliasMiningAnalyzeResponse(BaseModel):
    status: str
    proposals_generated: int
    total_feedback_analyzed: int
    proposals: list[AliasMiningProposalItem]


class AliasMiningProposalsResponse(BaseModel):
    total: int
    proposals: list[AliasMiningProposalItem]


class AliasMiningApplyRequest(BaseModel):
    reviewer: str | None = None
    notes: str | None = None


class AliasMiningApplyResponse(BaseModel):
    status: str
    proposal_id: str
    message: str


# ── Threshold Tuning ──────────────────────────────────────────────────────


class ThresholdChangeItem(BaseModel):
    parameter: str
    current_value: float
    proposed_value: float
    delta: float


class ImpactEstimateItem(BaseModel):
    metric: str
    current_value: float
    estimated_value: float
    improvement: float


class ThresholdProposalItem(BaseModel):
    id: str
    status: str
    proposal_type: str
    rationale: str
    changes: list[ThresholdChangeItem]
    estimated_impact: list[ImpactEstimateItem]
    confidence: float
    created_at: str


class ThresholdProposalAnalyzeRequest(BaseModel):
    pass


class ThresholdProposalResponse(BaseModel):
    status: str
    message: str
    proposals_generated: int
    proposals: list[ThresholdProposalItem]


class ThresholdProposalListResponse(BaseModel):
    total: int
    proposals: list[ThresholdProposalItem]


class ThresholdProposalApplyRequest(BaseModel):
    reviewer: str | None = None
    notes: str | None = None


class ThresholdProposalApplyResponse(BaseModel):
    status: str
    proposal_id: str
    message: str


# ── Shadow Mode Comparison ────────────────────────────────────────────────


class ShadowMetricComparisonItem(BaseModel):
    metric: str
    baseline: str
    shadow: str
    delta: str
    pct_change: str
    is_improvement: bool


class ShadowComparisonData(BaseModel):
    baseline_batch_id: str
    shadow_batch_id: str
    total_baseline: int
    total_shadow: int
    metric_comparisons: list[ShadowMetricComparisonItem]
    overall_improvement: str
    p_value: str
    is_statistically_significant: bool
    recommendation: str


class ShadowComparisonResponse(BaseModel):
    status: str
    message: str
    comparison: ShadowComparisonData | None


# ── Large-Scale Batch Processing (Fire-and-Forget) ────────────────────────────


class LargeBatchRequest(BaseModel):
    """Request to start a large-scale background batch processing job."""

    department: str | None = None
    workers: int = 3  # Concurrent workers (1-10)
    batch_size: int = 100  # PIDs per batch (10-1000)
    use_llm: bool = True  # Enable LLM disambiguation
    force: bool = False  # Re-match already-matched PIDs
    shadow_mode: bool = False  # Preview mode (don't write to DB)
    dry_run: bool = False  # Don't persist mappings


class LargeBatchResponse(BaseModel):
    """Immediate response when starting a background batch job."""

    status: str  # "queued"
    batch_id: str
    department: str | None
    message: str
    config: dict  # Returns the config for reference


class BatchJobStatusResponse(BaseModel):
    """Status of a background batch job."""

    batch_id: str
    department: str | None
    status: str  # "queued" | "running" | "completed" | "failed"
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_pids: int
    pids_matched: int
    pids_no_data: int
    pids_errored: int
    total_mappings_written: int
    status_counts: dict[str, int]
    error_message: str | None = None
    config: dict
    elapsed_seconds: float | None = None
    throughput_pids_per_sec: float | None = None


class BatchJobListResponse(BaseModel):
    """List of batch jobs."""

    total: int
    jobs: list[BatchJobStatusResponse]
