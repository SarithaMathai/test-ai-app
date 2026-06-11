"""Pydantic request/response schemas for the TCIN Mapper API."""

from __future__ import annotations

from pydantic import BaseModel

# ── Ingest ────────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    data_dir: str | None = None
    batch_size: int | None = None
    skip_existing: bool = True
    dry_run: bool = False
    chunk: str | None = None


class IngestResponse(BaseModel):
    status: str
    chunks_processed: int
    totals: dict[str, int]
    dry_run: bool


# ── Mapping run ───────────────────────────────────────────────────────────────

class MappingRunRequest(BaseModel):
    pid: str | None = None
    department: str | None = None
    force: bool = False
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
