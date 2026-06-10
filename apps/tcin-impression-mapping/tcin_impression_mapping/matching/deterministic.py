"""Deterministic fuzzy matching for TCIN color → impression name.

Uses rapidfuzz for string similarity. Returns a confidence score so the
mapper can decide whether to accept the match or escalate to the LLM.

Thresholds (tuneable via config):
  >= 0.85  → auto-accept (high confidence)
  0.60-0.85 → LLM fallback (ambiguous)
  < 0.60   → no match / human review
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

# Colour synonym map: used to expand the search before fuzzy scoring.
# Keys are normalised to lower-case. Values are additional terms to try.
_SYNONYMS: dict[str, list[str]] = {
    "red": ["ruby", "crimson", "scarlet", "garnet", "cherry", "strawberry"],
    "pink": ["rose", "blush", "peony", "flamingo", "raspberry", "coral"],
    "blue": ["navy", "cobalt", "azure", "sapphire", "indigo", "teal", "denim"],
    "green": ["olive", "forest", "sage", "mint", "jade", "emerald", "moss"],
    "yellow": ["gold", "mustard", "amber", "honey", "sunflower", "lemon"],
    "orange": ["tangerine", "peach", "apricot", "mango", "pumpkin", "sunset"],
    "brown": ["chocolate", "coffee", "mocha", "caramel", "chestnut", "tan"],
    "gray": ["silver", "charcoal", "slate", "graphite", "ash", "smoke"],
    "grey": ["silver", "charcoal", "slate", "graphite", "ash", "smoke"],
    "black": ["onyx", "ebony", "midnight", "jet", "obsidian"],
    "white": ["ivory", "cream", "pearl", "vanilla", "snow", "alabaster"],
    "beige": ["nude", "oatmeal", "almond", "sand", "ecru", "natural", "linen"],
    "multi": ["multicolor", "assorted", "print", "pattern", "floral", "tropical"],
}


@dataclass
class DeterministicMatch:
    impression: str
    score: float  # 0.0 - 1.0 normalised
    reason: str


def find_best_match(
    color_name: str,
    color_family: str,
    candidates: list[str],
    *,
    auto_threshold: float = 0.85,
    min_threshold: float = 0.40,
) -> DeterministicMatch | None:
    """Return the best impression candidate or None if no candidate clears min_threshold.

    Scoring strategy (tried in order, first clear win is returned):
    1. Exact case-insensitive containment (score = 1.0)
    2. Synonym containment (score = 0.90)
    3. rapidfuzz token_sort_ratio on color_name + color_family combined
    """
    try:
        from rapidfuzz import fuzz
    except ImportError as exc:
        raise ImportError(
            "rapidfuzz is not installed. Add 'rapidfuzz' to your dependencies."
        ) from exc

    lower_color = color_name.lower().strip()
    lower_family = color_family.lower().strip()
    query = f"{lower_color} {lower_family}".strip()

    synonyms_for_color = _build_synonyms(lower_color, lower_family)

    best: DeterministicMatch | None = None

    for candidate in candidates:
        lower_cand = candidate.lower()

        # Strategy 1: exact containment
        if lower_color in lower_cand or lower_cand in lower_color:
            score = 1.0
            reason = f"'{lower_color}' contained in impression name"
            _update_best(best, DeterministicMatch(candidate, score, reason))
            best = DeterministicMatch(candidate, score, reason)
            continue

        # Strategy 2: synonym containment
        for syn in synonyms_for_color:
            if syn in lower_cand:
                score = 0.90
                reason = f"synonym '{syn}' of '{lower_color}' found in impression"
                match = DeterministicMatch(candidate, score, reason)
                if best is None or match.score > best.score:
                    best = match
                break

        # Strategy 3: fuzzy ratio
        ratio = fuzz.token_sort_ratio(query, lower_cand) / 100.0
        if ratio >= min_threshold:
            match = DeterministicMatch(candidate, ratio, f"fuzzy score {ratio:.2f} for '{query}'")
            if best is None or match.score > best.score:
                best = match

    if best is None or best.score < min_threshold:
        return None

    log.debug(
        "Deterministic match: color=%s → %s (score=%.2f)",
        color_name,
        best.impression,
        best.score,
    )
    return best


def _build_synonyms(color: str, family: str) -> list[str]:
    """Return synonym terms to check for the given color and family."""
    terms: list[str] = []
    for word in (color, family):
        terms.extend(_SYNONYMS.get(word, []))
        # Also check if the word contains a known key
        for key, syns in _SYNONYMS.items():
            if key in word:
                terms.extend(syns)
    return list(dict.fromkeys(terms))  # deduplicate, preserve order


def _update_best(
    current: DeterministicMatch | None, candidate: DeterministicMatch
) -> DeterministicMatch:
    if current is None or candidate.score > current.score:
        return candidate
    return current
