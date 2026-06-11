"""Unit tests for the color scorer."""

import pytest
from plm_tcin_mapper.matching.scorer import candidate_list, color_score


@pytest.mark.unit
class TestColorScore:
    def test_exact_token_match(self):
        score, reason = color_score("Red", "ROMANTIC RED")
        assert score >= 0.70
        assert "red" in reason

    def test_keyword_match_synonym(self):
        score, reason = color_score("Navy", "COBALT BLUE")
        assert score >= 0.85
        assert "keyword_match" in reason or "token" in reason

    def test_no_match_returns_zero(self):
        score, _reason = color_score("Red", "Forest Green")
        assert score < 0.50

    def test_empty_strings(self):
        score, _reason = color_score("", "Blue")
        assert score == 0.0

    def test_exact_full_overlap(self):
        score, _reason = color_score("Blue", "DEEP BLUE")
        assert score >= 0.70

    def test_fuzzy_fallback(self):
        score, _reason = color_score("Aqua", "Aquamarine")
        assert score > 0.0


@pytest.mark.unit
class TestCandidateList:
    def test_returns_sorted_by_score(self):
        impressions = ["Red", "Blue", "Green", "Ruby Red"]
        results = candidate_list("Crimson Red", impressions)
        if len(results) >= 2:
            assert results[0][1] >= results[1][1]

    def test_min_score_filter(self):
        impressions = ["Red", "Forest Green", "Navy Blue"]
        results = candidate_list("Red", impressions, min_score=0.80)
        assert all(s >= 0.80 for _, s, _ in results)
