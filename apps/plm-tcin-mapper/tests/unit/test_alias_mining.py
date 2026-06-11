"""Unit tests for alias mining service."""

from __future__ import annotations

from unittest.mock import MagicMock
from datetime import UTC, datetime

import pytest

from plm_tcin_mapper.database.models import FeedbackAction, ProposalStatus, ProposalType
from plm_tcin_mapper.models.schemas import AliasMiningAnalyzeRequest
from plm_tcin_mapper.services.alias_mining_service import AliasMiningService, KeywordCorrection


@pytest.fixture
def mock_mongo():
    mongo = MagicMock()
    mongo.get_sync_db.return_value = MagicMock()
    return mongo


@pytest.fixture
def keyword_map():
    return {
        "red": "red",
        "ruby": "red",
        "maroon": "red",
        "purple": "purple",
        "violet": "purple",
        "pink": "pink",
        "blue": "blue",
        "navy": "blue",
    }


@pytest.fixture
def alias_mining_service(mock_mongo, keyword_map):
    return AliasMiningService(mongo=mock_mongo, keyword_map=keyword_map)


class TestKeywordCorrection:
    def test_initialization(self):
        kc = KeywordCorrection()
        assert kc.frequency == 0
        assert kc.correction_count == 0
        assert kc.target_colors == {}
        assert kc.supporting_feedback_ids == []

    def test_add_observation_correction(self):
        kc = KeywordCorrection()
        kc.add_observation(
            original_color="red",
            suggested_colors={"purple"},
            is_correction=True,
            feedback_id="fb1",
        )
        assert kc.frequency == 1
        assert kc.correction_count == 1
        assert kc.target_colors["purple"] == 1
        assert "fb1" in kc.supporting_feedback_ids

    def test_add_observation_non_correction(self):
        kc = KeywordCorrection()
        kc.add_observation(
            original_color="red",
            suggested_colors={"red"},
            is_correction=False,
            feedback_id="fb1",
        )
        assert kc.frequency == 1
        assert kc.correction_count == 0
        assert len(kc.target_colors) == 0

    def test_correction_rate(self):
        kc = KeywordCorrection()
        kc.add_observation("red", {"purple"}, True, "fb1")
        kc.add_observation("red", {"purple"}, True, "fb2")
        kc.add_observation("red", {"red"}, False, "fb3")
        assert kc.correction_rate == pytest.approx(0.667, rel=0.01)

    def test_most_common_target_color(self):
        kc = KeywordCorrection()
        kc.add_observation("red", {"purple", "violet"}, True, "fb1")
        kc.add_observation("red", {"purple"}, True, "fb2")
        kc.add_observation("red", {"pink"}, True, "fb3")
        assert kc.most_common_target_color == "purple"

    def test_most_common_target_color_empty(self):
        kc = KeywordCorrection()
        assert kc.most_common_target_color is None


class TestAliasMiningService:
    def test_extract_keyword_patterns_basic(self, alias_mining_service):
        feedback = [
            {
                "_id": "fb1",
                "original_impression_name": "RUBY RED",
                "suggested_impression_name": "PURPLE VIOLET",
                "action": "CORRECT",
            },
            {
                "_id": "fb2",
                "original_impression_name": "MAROON WINE",
                "suggested_impression_name": "NAVY BLUE",
                "action": "CORRECT",
            },
        ]

        patterns = alias_mining_service._extract_keyword_patterns(feedback)

        assert "ruby" in patterns
        assert "maroon" in patterns
        assert patterns["ruby"].frequency >= 1
        assert patterns["maroon"].frequency >= 1

    def test_extract_keyword_patterns_empty(self, alias_mining_service):
        patterns = alias_mining_service._extract_keyword_patterns([])
        assert patterns == {}

    def test_extract_keyword_patterns_missing_fields(self, alias_mining_service):
        feedback = [
            {"_id": "fb1", "original_impression_name": "RED"},
        ]
        patterns = alias_mining_service._extract_keyword_patterns(feedback)
        assert patterns == {}

    def test_generate_proposals_frequency_threshold(self, alias_mining_service):
        corrections = {
            "ruby": KeywordCorrection(),
            "navy": KeywordCorrection(),
        }
        corrections["ruby"].add_observation("red", {"purple"}, True, "fb1")
        corrections["ruby"].add_observation("red", {"purple"}, True, "fb2")
        corrections["ruby"].add_observation("red", {"purple"}, True, "fb3")

        corrections["navy"].add_observation("blue", {"green"}, True, "fb4")

        proposals = alias_mining_service._generate_proposals(
            corrections,
            min_frequency=3,
            min_confidence=0.5,
        )

        assert len(proposals) >= 1
        assert any(p.keyword == "ruby" for p in proposals)
        assert not any(p.keyword == "navy" for p in proposals)

    def test_generate_proposals_confidence_threshold(self, alias_mining_service):
        corrections = {
            "ruby": KeywordCorrection(),
        }
        corrections["ruby"].add_observation("red", {"purple"}, True, "fb1")
        corrections["ruby"].add_observation("red", {"red"}, False, "fb2")
        corrections["ruby"].add_observation("red", {"red"}, False, "fb3")

        proposals = alias_mining_service._generate_proposals(
            corrections,
            min_frequency=1,
            min_confidence=0.8,
        )

        assert len(proposals) == 0

    def test_generate_proposals_sorting(self, alias_mining_service):
        corrections = {
            "ruby": KeywordCorrection(),
            "maroon": KeywordCorrection(),
        }
        for _ in range(5):
            corrections["ruby"].add_observation("red", {"purple"}, True, "")
        for _ in range(3):
            corrections["maroon"].add_observation("red", {"purple"}, True, "")

        proposals = alias_mining_service._generate_proposals(
            corrections,
            min_frequency=1,
            min_confidence=0.5,
        )

        if len(proposals) >= 2:
            assert proposals[0].frequency >= proposals[1].frequency

    def test_generate_proposals_limit(self, alias_mining_service):
        corrections = {}
        for i in range(10):
            corrections[f"keyword{i}"] = KeywordCorrection()
            for _ in range(5):
                corrections[f"keyword{i}"].add_observation("red", {"purple"}, True, "")

        proposals = alias_mining_service._generate_proposals(
            corrections,
            min_frequency=1,
            min_confidence=0.5,
            limit=3,
        )

        assert len(proposals) == 3

    def test_estimate_impact_high(self, alias_mining_service):
        impact = alias_mining_service._estimate_impact("ruby", "red", "purple", 15)
        assert "HIGH" in impact

    def test_estimate_impact_medium(self, alias_mining_service):
        impact = alias_mining_service._estimate_impact("ruby", "red", "purple", 7)
        assert "MEDIUM" in impact

    def test_estimate_impact_low(self, alias_mining_service):
        impact = alias_mining_service._estimate_impact("ruby", "red", "purple", 2)
        assert "LOW" in impact

    def test_proposal_attributes(self, alias_mining_service):
        corrections = {
            "ruby": KeywordCorrection(),
        }
        for _ in range(5):
            corrections["ruby"].add_observation("red", {"purple"}, True, "fb1")

        proposals = alias_mining_service._generate_proposals(
            corrections,
            min_frequency=1,
            min_confidence=0.5,
        )

        assert len(proposals) > 0
        proposal = proposals[0]
        assert proposal.proposal_type == ProposalType.ALIAS_MOVE
        assert proposal.status == ProposalStatus.PENDING
        assert proposal.base_color == "red"
        assert proposal.keyword == "ruby"
        assert proposal.suggested_base_color == "purple"
        assert proposal.frequency == 5
        assert proposal.confidence == 1.0
        assert "ruby" in proposal.rationale
        assert proposal.estimated_impact is not None


class TestAliasMiningServiceIntegration:
    def test_analyze_sync_with_mock_data(self, mock_mongo, keyword_map):
        db = mock_mongo.get_sync_db.return_value
        feedback_col = MagicMock()
        proposals_col = MagicMock()

        db.__getitem__.side_effect = lambda key: {
            "feedback": feedback_col,
            "alias_mining_proposals": proposals_col,
        }[key]

        feedback_col.find.return_value = [
            {
                "_id": "fb1",
                "action": "CORRECT",
                "original_impression_name": "RUBY RED",
                "suggested_impression_name": "PURPLE VIOLET",
            },
            {
                "_id": "fb2",
                "action": "CORRECT",
                "original_impression_name": "MAROON WINE",
                "suggested_impression_name": "PURPLE VIOLET",
            },
            {
                "_id": "fb3",
                "action": "CORRECT",
                "original_impression_name": "CRIMSON SCARLET",
                "suggested_impression_name": "PURPLE VIOLET",
            },
        ]

        service = AliasMiningService(mongo=mock_mongo, keyword_map=keyword_map)
        request = AliasMiningAnalyzeRequest(min_frequency=2, min_confidence=0.5)

        response = service._analyze_sync(request)

        assert response.status == "ok"
        assert response.total_feedback_analyzed == 3
        assert response.proposals_generated >= 1
        assert len(response.proposals) >= 1
        assert proposals_col.insert_one.called
