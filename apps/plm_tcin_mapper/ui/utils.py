"""Shared UI helpers for the Streamlit operator app."""

from __future__ import annotations

_SIZE_ORDER = [
    "One Size",
    "XXS",
    "XX Small",
    "XS",
    "X Small",
    "S",
    "Small",
    "M",
    "Medium",
    "L",
    "Large",
    "XL",
    "X Large",
    "XXL",
    "XX Large",
    "XXXL",
    "1X",
    "2X",
    "3X",
    "4X",
    "5X",
    "0",
    "2",
    "4",
    "6",
    "8",
    "10",
    "12",
    "14",
    "16",
    "18",
    "20",
]


def size_sort_key(size: str) -> int:
    try:
        return _SIZE_ORDER.index(size)
    except ValueError:
        return 999


def confidence_badge(score: float) -> str:
    """Return an HTML pill badge with the numeric percentage, color-coded by tier.

    >= 85% -> green, 60-85% -> amber, < 60% -> red.
    """
    pct = round(score * 100)
    if score >= 0.85:
        bg, fg = "#d1f0d1", "#1a5c1a"
    elif score >= 0.60:
        bg, fg = "#fff3cd", "#7d5a00"
    else:
        bg, fg = "#fde8e8", "#8b1a1a"
    return (
        f'<span style="background:{bg};color:{fg};padding:3px 10px;'
        f"border-radius:20px;font-size:0.82em;font-weight:700;"
        f'display:inline-block;letter-spacing:0.02em">{pct}%</span>'
    )


def needs_review_icon(needs_review: bool, avg_conf: float) -> str:
    """Traffic-light icon for expander headers (plain text, no HTML)."""
    if needs_review:
        return "🔴"
    if avg_conf >= 0.85:
        return "🟢"
    return "🟡"
