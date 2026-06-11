"""Deterministic matching engine — three-round Hungarian algorithm.

Runs greedy high-confidence assignment → Hungarian optimal assignment →
fallback (best-available) for each PID's TCIN x impression matrix.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment

from plm_tcin_mapper.database.models import (
    ColorCandidate,
    Mapping,
    MappingStatus,
    MatchRound,
    TcinRecord,
    VariationRecord,
)
from plm_tcin_mapper.matching.color_keywords import get_merged_keyword_map
from plm_tcin_mapper.matching.scorer import (
    HIGH_CONF_THRESHOLD,
    build_score_matrix,
    candidate_list,
    color_score,
)
from plm_tcin_mapper.matching.size_normalizer import best_size_match


def match_pid_records(
    tcin_records: list[TcinRecord],
    variation_records: list[VariationRecord],
    cfg: Any,
) -> list[dict]:
    """Run the full three-round deterministic matching pipeline for one PID.

    Returns a list of raw dicts with fields expected by the Mapping model.
    """
    if not tcin_records or not variation_records:
        return []

    _, keyword_to_base = get_merged_keyword_map()

    distinct_colors = _distinct_ordered([r.color_name for r in tcin_records])
    distinct_impressions = _distinct_ordered([r.impression_name for r in variation_records])

    if len(distinct_impressions) == 1:
        imp = distinct_impressions[0]
        assignments = dict.fromkeys(distinct_colors, imp)
        assignment_rounds: dict[str, MatchRound] = dict.fromkeys(distinct_colors, MatchRound.GREEDY)
        scores_map: dict[tuple[str, str], float] = {}
        reasons_map: dict[tuple[str, str], str] = {}
        for cn in distinct_colors:
            s, r = color_score(cn, imp, keyword_to_base)
            scores_map[(cn, imp)] = s
            reasons_map[(cn, imp)] = r
    else:
        score_matrix, reason_matrix = build_score_matrix(distinct_colors, distinct_impressions, keyword_to_base)
        scores_map = {}
        reasons_map = {}
        for i, cn in enumerate(distinct_colors):
            for j, imp in enumerate(distinct_impressions):
                scores_map[(cn, imp)] = score_matrix[i][j]
                reasons_map[(cn, imp)] = reason_matrix[i][j]
        assignments, assignment_rounds = _three_round_assign(distinct_colors, distinct_impressions, score_matrix)

    tcin_by_color: dict[str, list[TcinRecord]] = {}
    for r in tcin_records:
        tcin_by_color.setdefault(r.color_name, []).append(r)

    var_by_impression: dict[str, list[VariationRecord]] = {}
    for r in variation_records:
        var_by_impression.setdefault(r.impression_name, []).append(r)

    results: list[dict] = []
    for color_name, impression_name in assignments.items():
        color_conf = scores_map.get((color_name, impression_name), 0.0)
        match_reason = reasons_map.get((color_name, impression_name), "")
        match_round = assignment_rounds.get(color_name, MatchRound.FALLBACK)

        candidates = candidate_list(color_name, distinct_impressions, keyword_to_base, min_score=0.20)
        color_possible_values = [
            ColorCandidate(impression_name=c, score=s, reason=r) for c, s, r in candidates
        ]

        var_records_for_imp = var_by_impression.get(impression_name, [])
        var_sizes = [v.size for v in var_records_for_imp]

        for tcin in tcin_by_color.get(color_name, []):
            best_var_size, size_conf = best_size_match(tcin.size, var_sizes)

            matched_var: VariationRecord | None = None
            for v in var_records_for_imp:
                if v.size == best_var_size:
                    matched_var = v
                    break

            tier = Mapping.tier_from_score(color_conf)
            status = _assign_status(color_conf, cfg)

            results.append({
                "pid": tcin.pid,
                "tcin_id": tcin.tcin_id,
                "partner_id": tcin.partner_id,
                "department_ids": tcin.department_ids or [],
                "tcin_color": tcin.color,
                "tcin_color_name": color_name,
                "tcin_size": tcin.size,
                "matched_impression_id": matched_var.impression_id if matched_var else None,
                "matched_impression_name": impression_name,
                "variation_size_id": matched_var.size_id if matched_var else None,
                "variation_size": best_var_size or None,
                "workspace_ids": matched_var.workspace_ids if matched_var else [],
                "color_confidence": round(color_conf, 4),
                "size_confidence": round(size_conf, 4),
                "confidence_tier": tier,
                "color_match_reason": match_reason,
                "color_possible_values": color_possible_values,
                "match_round": match_round,
                "status": status,
                "candidates": [c.impression_name for c in color_possible_values],
                "used_llm": False,
            })

    return results


def _three_round_assign(
    colors: list[str],
    impressions: list[str],
    score_matrix: list[list[float]],
) -> tuple[dict[str, str], dict[str, MatchRound]]:
    mat = np.array(score_matrix, dtype=float)
    n_colors = len(colors)
    n_imps = len(impressions)

    assigned_colors: set[int] = set()
    assigned_impressions: set[int] = set()
    assignment: dict[str, str] = {}
    rounds: dict[str, MatchRound] = {}

    # Round 1: Greedy high-confidence
    high_conf_pairs = [
        (mat[ci, ii], ci, ii)
        for ci in range(n_colors)
        for ii in range(n_imps)
        if mat[ci, ii] >= HIGH_CONF_THRESHOLD
    ]
    high_conf_pairs.sort(reverse=True)
    for _score, ci, ii in high_conf_pairs:
        if ci not in assigned_colors and ii not in assigned_impressions:
            assignment[colors[ci]] = impressions[ii]
            rounds[colors[ci]] = MatchRound.GREEDY
            assigned_colors.add(ci)
            assigned_impressions.add(ii)

    # Round 2: Hungarian on remainder
    remaining_ci = [ci for ci in range(n_colors) if ci not in assigned_colors]
    remaining_ii = [ii for ii in range(n_imps) if ii not in assigned_impressions]
    if remaining_ci and remaining_ii:
        sub_mat = mat[np.ix_(remaining_ci, remaining_ii)]
        row_ind, col_ind = linear_sum_assignment(-sub_mat)
        for r, c in zip(row_ind, col_ind, strict=False):
            ci = remaining_ci[r]
            ii = remaining_ii[c]
            if mat[ci, ii] > 0.0:
                assignment[colors[ci]] = impressions[ii]
                rounds[colors[ci]] = MatchRound.HUNGARIAN
                assigned_colors.add(ci)
                assigned_impressions.add(ii)

    # Round 3: Fallback
    for ci in range(n_colors):
        if ci not in assigned_colors:
            best_ii = int(np.argmax(mat[ci]))
            assignment[colors[ci]] = impressions[best_ii]
            rounds[colors[ci]] = MatchRound.FALLBACK

    return assignment, rounds


def _distinct_ordered(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _assign_status(color_confidence: float, cfg: Any) -> MappingStatus:
    t = cfg.matching
    if color_confidence >= t.auto_confirm_threshold:
        return MappingStatus.AUTO_CONFIRM
    if color_confidence >= t.llm_fallback_threshold:
        return MappingStatus.NEEDS_SPOT_CHECK
    return MappingStatus.NEEDS_REVIEW
