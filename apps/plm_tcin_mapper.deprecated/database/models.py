"""Pydantic models for all MongoDB collections used by the TCIN Mapper."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid4())


# ─── Enums ────────────────────────────────────────────────────────────────────


class MappingStatus(StrEnum):
    AUTO_CONFIRM = "AUTO_CONFIRM"
    LLM_ASSISTED = "LLM_ASSISTED"
    NEEDS_SPOT_CHECK = "NEEDS_SPOT_CHECK"
    NO_MATCH = "NO_MATCH"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CORRECTED = "CORRECTED"


class ConfidenceTier(StrEnum):
    HIGH = "HIGH"
    GOOD = "GOOD"
    FAIR = "FAIR"
    LOW = "LOW"


class FeedbackAction(StrEnum):
    CONFIRM = "CONFIRM"
    REJECT = "REJECT"
    CORRECT = "CORRECT"


class MatchRound(StrEnum):
    GREEDY = "GREEDY"
    HUNGARIAN = "HUNGARIAN"
    FALLBACK = "FALLBACK"
    LLM = "LLM"


class ProposalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"


class ProposalType(StrEnum):
    ALIAS_ADD = "ALIAS_ADD"
    ALIAS_MOVE = "ALIAS_MOVE"
    THRESHOLD_ADJUST = "THRESHOLD_ADJUST"


# ─── Collection: tcin_records ─────────────────────────────────────────────────


class TcinRecord(BaseModel):
    id: str = Field(default_factory=_new_id, alias="_id")
    pid: str
    partner_id: str | None = None
    tcin_id: str
    color: str
    color_name: str
    size: str
    department_ids: list[str] = []
    class_ids: list[str] = []
    ingested_at: datetime = Field(default_factory=_utcnow)
    source_file: str | None = None

    model_config = {"populate_by_name": True}


# ─── Collection: variation_records ───────────────────────────────────────────


class VariationRecord(BaseModel):
    id: str = Field(default_factory=_new_id, alias="_id")
    pid: str
    impression_id: str
    impression_name: str
    size_id: str | None = None
    size: str
    workspace_ids: list[str] = []
    ingested_at: datetime = Field(default_factory=_utcnow)
    source_file: str | None = None

    model_config = {"populate_by_name": True}


# ─── Collection: mappings ────────────────────────────────────────────────────


class ColorCandidate(BaseModel):
    impression_name: str
    score: float
    reason: str


class Mapping(BaseModel):
    id: str = Field(default_factory=_new_id, alias="_id")
    pid: str
    tcin_id: str
    partner_id: str | None = None
    department_ids: list[str] = []

    tcin_color: str
    tcin_color_name: str
    tcin_size: str

    matched_impression_id: str | None = None
    matched_impression_name: str | None = None
    variation_size_id: str | None = None
    variation_size: str | None = None
    workspace_ids: list[str] = []

    color_confidence: float = 0.0
    size_confidence: float = 0.0
    confidence_tier: ConfidenceTier = ConfidenceTier.LOW
    color_match_reason: str | None = None
    color_possible_values: list[ColorCandidate] = []

    match_round: MatchRound | None = None
    llm_rationale: str | None = None
    llm_call_id: str | None = None
    batch_id: str | None = None
    status: MappingStatus = MappingStatus.NEEDS_REVIEW

    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    model_config = {"populate_by_name": True}

    @classmethod
    def tier_from_score(cls, score: float) -> ConfidenceTier:
        if score >= 0.85:
            return ConfidenceTier.HIGH
        if score >= 0.70:
            return ConfidenceTier.GOOD
        if score >= 0.50:
            return ConfidenceTier.FAIR
        return ConfidenceTier.LOW


# ─── Collection: feedback ────────────────────────────────────────────────────


class FeedbackRecord(BaseModel):
    id: str = Field(default_factory=_new_id, alias="_id")
    mapping_id: str
    pid: str
    tcin_id: str
    action: FeedbackAction
    reviewer: str | None = None
    notes: str | None = None

    tcin_color: str | None = None
    tcin_color_name: str | None = None
    tcin_size: str | None = None
    department_ids: list[str] = []
    match_round: str | None = None
    original_confidence_tier: str | None = None

    suggested_impression_id: str | None = None
    suggested_impression_name: str | None = None
    original_impression_name: str | None = None
    original_color_confidence: float | None = None

    was_correct: bool | None = None

    created_at: datetime = Field(default_factory=_utcnow)

    model_config = {"populate_by_name": True}


# ─── Collection: eval_runs ───────────────────────────────────────────────────


class EvalRun(BaseModel):
    id: str = Field(default_factory=_new_id, alias="_id")
    total_mappings: int = 0
    by_status: dict[str, int] = {}
    by_tier: dict[str, int] = {}
    pct_high: float = 0.0
    pct_good: float = 0.0
    pct_fair: float = 0.0
    pct_low: float = 0.0
    pct_confirmed: float = 0.0
    pct_rejected: float = 0.0
    correction_rate: float = 0.0
    avg_color_confidence: float = 0.0
    guardrail_alerts: list[str] = []
    created_at: datetime = Field(default_factory=_utcnow)

    model_config = {"populate_by_name": True}


# ─── Collection: llm_calls ──────────────────────────────────────────────────


class LLMCallRecord(BaseModel):
    id: str = Field(default_factory=_new_id, alias="_id")
    mapping_id: str | None = None
    pid: str
    tcin_id: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cost: float = 0.0

    chosen_impression: str
    confidence: float
    reasoning: str
    user_prompt: str | None = None
    raw_response: str | None = None

    created_at: datetime = Field(default_factory=_utcnow)

    model_config = {"populate_by_name": True}


# ─── Collection: extended_eval_runs ──────────────────────────────────────


class SignalAccuracy(BaseModel):
    signal_type: str
    occurrences: int
    corrections: int
    correction_rate: float
    avg_confidence: float
    confidence_by_tier: dict[str, int] = {}


class DepartmentMetrics(BaseModel):
    department: str
    total_mappings: int
    pct_high_confidence: float
    correction_rate: float
    avg_confidence: float
    by_match_round: dict[str, int] = {}


class LLMImpactMetrics(BaseModel):
    total_llm_calls: int
    llm_corrected: int
    llm_correction_rate: float
    llm_avg_confidence: float
    deterministic_corrected: int
    deterministic_correction_rate: float
    llm_vs_deterministic_improvement: float


class ExtendedEvalRun(BaseModel):
    id: str = Field(default_factory=_new_id, alias="_id")
    eval_run_id: str | None = None

    total_mappings: int = 0
    by_status: dict[str, int] = {}
    by_tier: dict[str, int] = {}
    pct_high: float = 0.0
    pct_good: float = 0.0
    pct_fair: float = 0.0
    pct_low: float = 0.0
    avg_color_confidence: float = 0.0
    correction_rate: float = 0.0

    per_signal_accuracy: dict[str, SignalAccuracy] = {}
    per_department_metrics: list[DepartmentMetrics] = []
    llm_impact: LLMImpactMetrics | None = None

    confidence_calibration_error: float = 0.0
    high_confidence_actual_correction_rate: float = 0.0
    low_confidence_actual_correction_rate: float = 0.0

    guardrail_alerts: list[str] = []
    created_at: datetime = Field(default_factory=_utcnow)

    model_config = {"populate_by_name": True}


# ─── Collection: shadow_comparisons ──────────────────────────────────────


class ShadowMetricComparison(BaseModel):
    metric: str
    baseline_value: float
    shadow_value: float
    delta: float
    pct_change: float
    is_improvement: bool


class ShadowComparisonResult(BaseModel):
    id: str = Field(default_factory=_new_id, alias="_id")
    baseline_batch_id: str
    shadow_batch_id: str

    total_baseline_mappings: int
    total_shadow_mappings: int

    metric_comparisons: list[ShadowMetricComparison] = []

    confidence_improvement: float = 0.0
    correction_rate_improvement: float = 0.0
    pct_high_improvement: float = 0.0

    overall_improvement_score: float = 0.0
    p_value: float = 1.0
    is_statistically_significant: bool = False

    recommendation: str = ""

    created_at: datetime = Field(default_factory=_utcnow)

    model_config = {"populate_by_name": True}


# ─── Collection: threshold_proposals ──────────────────────────────────────


class ThresholdChange(BaseModel):
    parameter: str
    current_value: float
    proposed_value: float
    delta: float


class ImpactEstimate(BaseModel):
    metric: str
    current_value: float
    estimated_value: float
    improvement: float


class ThresholdProposal(BaseModel):
    id: str = Field(default_factory=_new_id, alias="_id")
    status: ProposalStatus = ProposalStatus.PENDING

    eval_run_id: str
    proposal_type: str
    rationale: str

    changes: list[ThresholdChange] = []
    estimated_impact: list[ImpactEstimate] = []
    confidence: float = 0.0

    supporting_metrics: dict[str, float] = {}
    test_batch_id: str | None = None
    actual_results: dict[str, float] = {}

    created_at: datetime = Field(default_factory=_utcnow)
    applied_at: datetime | None = None

    model_config = {"populate_by_name": True}


# ─── Collection: alias_mining_proposals ─────────────────────────────────


class AliasMiningProposal(BaseModel):
    id: str = Field(default_factory=_new_id, alias="_id")
    proposal_type: ProposalType
    status: ProposalStatus = ProposalStatus.PENDING

    base_color: str
    keyword: str
    suggested_base_color: str | None = None

    frequency: int
    confidence: float
    supporting_feedback_ids: list[str] = []

    rationale: str
    estimated_impact: str | None = None

    created_at: datetime = Field(default_factory=_utcnow)
    applied_at: datetime | None = None

    model_config = {"populate_by_name": True}
