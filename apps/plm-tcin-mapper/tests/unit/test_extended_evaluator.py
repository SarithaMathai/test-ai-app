"""Unit tests for extended evaluation metrics."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from plm_tcin_mapper.database.models import ConfidenceTier, MappingStatus, MatchRound
from plm_tcin_mapper.pipeline.extended_evaluator import (
    _compute_calibration_error,
    _compute_llm_impact,
    _compute_per_department_metrics,
    _compute_per_signal_accuracy,
    _extract_signal_type,
)


class TestSignalTypeExtraction:
    def test_extract_token_overlap_signals(self):
        assert _extract_signal_type("exact_token:ruby") == "token_overlap"
        assert _extract_signal_type("token_overlap:red") == "token_overlap"
        assert _extract_signal_type("stem_token:red") == "token_overlap"
        assert _extract_signal_type("stem_overlap:ruby") == "token_overlap"

    def test_extract_keyword_match_signal(self):
        assert _extract_signal_type("keyword_match:red") == "keyword_match"

    def test_extract_fuzzy_signals(self):
        assert _extract_signal_type("fuzzy:0.75") == "fuzzy_match"
        assert _extract_signal_type("fuzzy_fallback:0.65") == "fuzzy_match"
        assert _extract_signal_type("wratio:0.70") == "fuzzy_match"

    def test_extract_unknown_signal(self):
        assert _extract_signal_type("unknown:xyz") == "unknown"
        assert _extract_signal_type("") == "unknown"
        assert _extract_signal_type("random") == "random"


class TestPerSignalAccuracy:
    def test_single_signal_type(self):
        mappings = [
            {
                "_id": "m1",
                "color_match_reason": "token_overlap:ruby",
                "color_confidence": 0.95,
                "confidence_tier": "HIGH",
            },
            {
                "_id": "m2",
                "color_match_reason": "token_overlap:red",
                "color_confidence": 0.90,
                "confidence_tier": "HIGH",
            },
        ]
        feedback_by_mapping = {
            "m1": [{"action": "CORRECT"}],
            "m2": [],
        }

        result = _compute_per_signal_accuracy(mappings, feedback_by_mapping)

        assert "token_overlap" in result
        metric = result["token_overlap"]
        assert metric.occurrences == 2
        assert metric.corrections == 1
        assert metric.correction_rate == pytest.approx(0.5)
        assert metric.avg_confidence == pytest.approx(0.925, rel=0.01)

    def test_multiple_signal_types(self):
        mappings = [
            {
                "_id": "m1",
                "color_match_reason": "token_overlap:ruby",
                "color_confidence": 0.95,
                "confidence_tier": "HIGH",
            },
            {
                "_id": "m2",
                "color_match_reason": "keyword_match:red",
                "color_confidence": 0.85,
                "confidence_tier": "GOOD",
            },
            {
                "_id": "m3",
                "color_match_reason": "fuzzy_fallback:0.65",
                "color_confidence": 0.65,
                "confidence_tier": "FAIR",
            },
        ]
        feedback_by_mapping = {}

        result = _compute_per_signal_accuracy(mappings, feedback_by_mapping)

        assert len(result) == 3
        assert "token_overlap" in result
        assert "keyword_match" in result
        assert "fuzzy_match" in result

    def test_no_mappings(self):
        result = _compute_per_signal_accuracy([], {})
        assert result == {}

    def test_missing_reason_field(self):
        mappings = [
            {
                "_id": "m1",
                "color_confidence": 0.95,
                "confidence_tier": "HIGH",
            },
        ]
        feedback_by_mapping = {}

        result = _compute_per_signal_accuracy(mappings, feedback_by_mapping)
        assert result == {}


class TestPerDepartmentMetrics:
    def test_single_department(self):
        mappings = [
            {
                "_id": "m1",
                "department_ids": ["clothing"],
                "color_confidence": 0.95,
                "confidence_tier": "HIGH",
                "match_round": "GREEDY",
            },
            {
                "_id": "m2",
                "department_ids": ["clothing"],
                "color_confidence": 0.70,
                "confidence_tier": "GOOD",
                "match_round": "HUNGARIAN",
            },
        ]
        feedback_by_mapping = {}

        result = _compute_per_department_metrics(mappings, feedback_by_mapping)

        assert len(result) == 1
        metric = result[0]
        assert metric.department == "clothing"
        assert metric.total_mappings == 2
        assert metric.pct_high_confidence == pytest.approx(0.5)
        assert metric.avg_confidence == pytest.approx(0.825, rel=0.01)

    def test_multiple_departments(self):
        mappings = [
            {
                "_id": "m1",
                "department_ids": ["clothing", "shoes"],
                "color_confidence": 0.95,
                "confidence_tier": "HIGH",
                "match_round": "GREEDY",
            },
            {
                "_id": "m2",
                "department_ids": ["home"],
                "color_confidence": 0.70,
                "confidence_tier": "GOOD",
                "match_round": "HUNGARIAN",
            },
        ]
        feedback_by_mapping = {}

        result = _compute_per_department_metrics(mappings, feedback_by_mapping)

        assert len(result) == 3
        depts = {m.department for m in result}
        assert depts == {"clothing", "shoes", "home"}

    def test_department_correction_rate(self):
        mappings = [
            {
                "_id": "m1",
                "department_ids": ["clothing"],
                "color_confidence": 0.95,
                "confidence_tier": "HIGH",
                "match_round": "GREEDY",
            },
            {
                "_id": "m2",
                "department_ids": ["clothing"],
                "color_confidence": 0.70,
                "confidence_tier": "GOOD",
                "match_round": "HUNGARIAN",
            },
        ]
        feedback_by_mapping = {
            "m1": [{"action": "CORRECT"}],
            "m2": [],
        }

        result = _compute_per_department_metrics(mappings, feedback_by_mapping)

        metric = result[0]
        assert metric.correction_rate == pytest.approx(0.5)

    def test_unknown_department(self):
        mappings = [
            {
                "_id": "m1",
                "department_ids": [],
                "color_confidence": 0.95,
                "confidence_tier": "HIGH",
                "match_round": "GREEDY",
            },
        ]
        feedback_by_mapping = {}

        result = _compute_per_department_metrics(mappings, feedback_by_mapping)

        assert len(result) == 1
        assert result[0].department == "unknown"


class TestLLMImpact:
    def test_llm_vs_deterministic(self):
        mappings = [
            {
                "_id": "m1",
                "match_round": "LLM",
                "color_confidence": 0.85,
            },
            {
                "_id": "m2",
                "match_round": "LLM",
                "color_confidence": 0.80,
            },
            {
                "_id": "m3",
                "match_round": "GREEDY",
                "color_confidence": 0.95,
            },
            {
                "_id": "m4",
                "match_round": "HUNGARIAN",
                "color_confidence": 0.75,
            },
        ]
        feedback_by_mapping = {
            "m1": [{"action": "CORRECT"}],
            "m3": [{"action": "CORRECT"}],
        }

        result = _compute_llm_impact(mappings, feedback_by_mapping)

        assert result is not None
        assert result.total_llm_calls == 2
        assert result.llm_corrected == 1
        assert result.llm_correction_rate == pytest.approx(0.5)
        assert result.deterministic_corrected == 1
        assert result.deterministic_correction_rate == pytest.approx(0.5)

    def test_no_llm_calls(self):
        mappings = [
            {
                "_id": "m1",
                "match_round": "GREEDY",
                "color_confidence": 0.95,
            },
        ]
        feedback_by_mapping = {}

        result = _compute_llm_impact(mappings, feedback_by_mapping)
        assert result is None

    def test_llm_helping(self):
        """Test case where LLM improves accuracy."""
        mappings = [
            {
                "_id": "m1",
                "match_round": "LLM",
                "color_confidence": 0.85,
            },
            {
                "_id": "m2",
                "match_round": "LLM",
                "color_confidence": 0.80,
            },
            {
                "_id": "m3",
                "match_round": "GREEDY",
                "color_confidence": 0.95,
            },
            {
                "_id": "m4",
                "match_round": "GREEDY",
                "color_confidence": 0.90,
            },
        ]
        feedback_by_mapping = {
            "m3": [{"action": "CORRECT"}],
            "m4": [{"action": "CORRECT"}],
        }

        result = _compute_llm_impact(mappings, feedback_by_mapping)

        assert result is not None
        # LLM: 0 corrected / 2 = 0.0
        # Deterministic: 2 corrected / 2 = 1.0
        # Improvement: 1.0 - 0.0 = 1.0
        assert result.llm_correction_rate == pytest.approx(0.0)
        assert result.deterministic_correction_rate == pytest.approx(1.0)
        assert result.llm_vs_deterministic_improvement == pytest.approx(1.0)


class TestCalibrationError:
    def test_well_calibrated_confidence(self):
        """Test perfect calibration: high confidence = low correction rate."""
        mappings = [
            {
                "_id": f"m{i}",
                "color_confidence": 0.95,
            }
            for i in range(10)
        ] + [
            {
                "_id": f"m{i}",
                "color_confidence": 0.50,
            }
            for i in range(10, 20)
        ]
        feedback_by_mapping = {}

        ece = _compute_calibration_error(mappings, feedback_by_mapping)

        assert ece == pytest.approx(0.0, abs=0.05)

    def test_poorly_calibrated_confidence(self):
        """Test poor calibration: high confidence = high correction rate."""
        mappings = [
            {
                "_id": f"m{i}",
                "color_confidence": 0.95,
            }
            for i in range(10)
        ]
        feedback_by_mapping = {
            f"m{i}": [{"action": "CORRECT"}]
            for i in range(10)
        }

        ece = _compute_calibration_error(mappings, feedback_by_mapping)

        assert ece > 0.0

    def test_no_mappings(self):
        ece = _compute_calibration_error([], {})
        assert ece == 0.0
