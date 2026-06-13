"""Shared enums for Streamlit pages."""

from __future__ import annotations

from enum import Enum


class FeedbackAction(str, Enum):
    """Actions that can be taken on a mapping."""
    CONFIRM = "CONFIRM"
    REJECT = "REJECT"
    CORRECT = "CORRECT"


class MappingStatus(str, Enum):
    """Status values for mappings."""
    MATCHED = "MATCHED"
    NO_MATCH = "NO_MATCH"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CORRECTED = "CORRECTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NEEDS_SPOT_CHECK = "NEEDS_SPOT_CHECK"
