"""Data models for TCIN impression mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MatchStrategy(StrEnum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"
    NO_MATCH = "no_match"


@dataclass
class MappingRequest:
    """Input for a single TCIN → impression mapping attempt."""

    pid: str
    tcin_id: str
    color_family: str
    color_name: str
    size: str
    candidates: list[str]  # impression names to choose from
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class MappingResult:
    """Output of a mapping attempt."""

    pid: str
    tcin_id: str
    color_name: str
    chosen_impression: str
    confidence: float  # 0.0 - 1.0
    strategy: MatchStrategy
    reasoning: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.85

    @property
    def needs_review(self) -> bool:
        return self.confidence < 0.60 or self.strategy == MatchStrategy.NO_MATCH


@dataclass
class BatchResult:
    """Summary of a batch mapping run."""

    total: int = 0
    deterministic: int = 0
    llm_assisted: int = 0
    no_match: int = 0
    needs_review: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    results: list[MappingResult] = field(default_factory=list)

    @property
    def deterministic_pct(self) -> float:
        return self.deterministic / self.total if self.total else 0.0

    @property
    def llm_pct(self) -> float:
        return self.llm_assisted / self.total if self.total else 0.0
