"""Shared enums for Streamlit pages."""

from __future__ import annotations

from enum import StrEnum


class FeedbackAction(StrEnum):
    """Actions that can be taken on a mapping."""

    CONFIRM = "CONFIRM"
    REJECT = "REJECT"
    CORRECT = "CORRECT"


class MappingStatus(StrEnum):
    """Status values for mappings."""

    MATCHED = "MATCHED"
    NO_MATCH = "NO_MATCH"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CORRECTED = "CORRECTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NEEDS_SPOT_CHECK = "NEEDS_SPOT_CHECK"
