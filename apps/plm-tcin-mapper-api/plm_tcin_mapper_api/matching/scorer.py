"""Color similarity scorer.

Three cascading signals:
  1. Direct token overlap (highest priority) - 0.70-0.99
  2. Canonical base-color keyword match - 0.88-0.92
  3. Fuzzy string similarity fallback - penalised to <= 0.82
"""

from __future__ import annotations

from rapidfuzz import fuzz

from plm_tcin_mapper_api.matching.color_keywords import (
    COLOR_MODIFIERS,
    KEYWORD_TO_BASE,
    tokenize,
)

HIGH_CONF_THRESHOLD = 0.85
AUTO_CONFIRM_THRESHOLD = 0.90
LOW_CONF_THRESHOLD = 0.50
LLM_FALLBACK_THRESHOLD = 0.65
CANDIDATE_DEBATE_DELTA = 0.15


def color_score(
    color_name: str,
    impression_name: str,
    keyword_to_base: dict[str, str] | None = None,
) -> tuple[float, str]:
    """Score how well impression_name matches color_name. Returns (score, reason)."""
    if not color_name or not impression_name:
        return 0.0, "no_match"

    kb = keyword_to_base or KEYWORD_TO_BASE
    cn_tokens = set(tokenize(color_name))
    im_tokens = set(tokenize(impression_name))
    cn_core = cn_tokens - COLOR_MODIFIERS
    im_core = im_tokens - COLOR_MODIFIERS

    # Signal 1: Direct token overlap
    overlap = cn_core & im_core
    if overlap:
        if cn_core and cn_core <= im_core:
            return 0.99, f"exact_token:{','.join(sorted(overlap))}"
        fraction = len(overlap) / max(len(cn_core), 1)
        return round(0.70 + 0.29 * fraction, 3), f"token_overlap:{','.join(sorted(overlap))}"

    # Signal 1b: Stem overlap
    im_stemmed = {t[:-1] if t.endswith("s") and len(t) > 3 else t for t in im_core}
    stem_overlap = cn_core & im_stemmed
    if stem_overlap:
        fraction = len(stem_overlap) / max(len(cn_core), 1)
        if cn_core and cn_core <= im_stemmed:
            return 0.97, f"stem_token:{','.join(sorted(stem_overlap))}"
        return round(0.68 + 0.28 * fraction, 3), f"stem_overlap:{','.join(sorted(stem_overlap))}"

    # Signal 2: Canonical base-color keyword match
    cn_bases = {kb[t] for t in cn_core if t in kb}
    im_bases = {kb[t] for t in im_core if t in kb}
    im_stemmed_bases = {kb[t] for t in im_stemmed if t in kb}
    all_im_bases = im_bases | im_stemmed_bases

    base_overlap = cn_bases & all_im_bases
    if base_overlap:
        if len(cn_bases) == 1 and len(base_overlap) == 1:
            score = 0.92
        elif len(cn_bases) == 1:
            score = 0.90
        else:
            score = 0.88
        return score, f"keyword_match:{','.join(sorted(base_overlap))}"

    # Signal 3: Fuzzy fallback
    cn_lower = color_name.lower().strip()
    im_lower = impression_name.lower().strip()
    fuzzy_raw = (
        max(
            fuzz.token_set_ratio(cn_lower, im_lower),
            fuzz.partial_ratio(cn_lower, im_lower),
            fuzz.WRatio(cn_lower, im_lower),
        )
        / 100.0
    )

    if fuzzy_raw >= 0.60:
        penalty = 0.82 if (cn_bases or all_im_bases) else 0.75
        return round(fuzzy_raw * penalty, 3), f"fuzzy:{fuzzy_raw:.2f}"

    return 0.0, "no_match"


def build_score_matrix(
    color_names: list[str],
    impression_names: list[str],
    keyword_to_base: dict[str, str] | None = None,
) -> tuple[list[list[float]], list[list[str]]]:
    scores: list[list[float]] = []
    reasons: list[list[str]] = []
    for cn in color_names:
        row_s, row_r = [], []
        for im in impression_names:
            s, r = color_score(cn, im, keyword_to_base)
            row_s.append(s)
            row_r.append(r)
        scores.append(row_s)
        reasons.append(row_r)
    return scores, reasons


def candidate_list(
    color_name: str,
    impression_names: list[str],
    keyword_to_base: dict[str, str] | None = None,
    min_score: float = 0.25,
) -> list[tuple[str, float, str]]:
    results = []
    for imp in impression_names:
        s, r = color_score(color_name, imp, keyword_to_base)
        if s >= min_score:
            results.append((imp, s, r))
    results.sort(key=lambda x: -x[1])
    return results
