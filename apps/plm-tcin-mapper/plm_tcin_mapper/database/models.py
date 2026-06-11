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
