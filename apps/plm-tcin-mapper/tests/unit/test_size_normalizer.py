"""Unit tests for size normalizer."""

import pytest
from plm_tcin_mapper.matching.size_normalizer import best_size_match, normalize_size, size_similarity


@pytest.mark.unit
class TestNormalizeSize:
    def test_basic_sizes(self):
        assert normalize_size("Small").base == "s"
        assert normalize_size("Medium").base == "m"
        assert normalize_size("Large").base == "l"
        assert normalize_size("X Large").base == "xl"
        assert normalize_size("XX Large").base == "2xl"

    def test_modifier_detection(self):
        ns = normalize_size("Large Husky")
        assert ns.base == "l"
        assert ns.modifier == "husky"

    def test_one_size(self):
        assert normalize_size("One Size Fits Most").base == "os"
        assert normalize_size("OS").base == "os"

    def test_empty_string(self):
        ns = normalize_size("")
        assert ns.base == ""


@pytest.mark.unit
class TestSizeSimilarity:
    def test_exact_match(self):
        assert size_similarity("Large", "Large") == 1.0

    def test_same_base_different_modifier(self):
        score = size_similarity("Large", "Large Husky")
        assert score == 0.85

    def test_adjacent_sizes(self):
        score = size_similarity("Medium", "Large")
        assert score == 0.75

    def test_mismatched_sizes(self):
        score = size_similarity("Small", "XX Large")
        assert score < 0.5


@pytest.mark.unit
class TestBestSizeMatch:
    def test_finds_exact(self):
        best, score = best_size_match("Medium", ["Small", "Medium", "Large"])
        assert best == "Medium"
        assert score == 1.0

    def test_empty_list(self):
        best, score = best_size_match("Medium", [])
        assert best == ""
        assert score == 0.0
