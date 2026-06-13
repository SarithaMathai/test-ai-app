"""Alias mining service — analyzes feedback to propose keyword/alias improvements."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from ai_mongo import MongoClientManager

from plm_tcin_mapper.database.models import AliasMiningProposal, FeedbackAction, ProposalStatus, ProposalType
from plm_tcin_mapper.matching.color_keywords import tokenize
from plm_tcin_mapper.models.schemas import (
    AliasMiningAnalyzeRequest,
    AliasMiningAnalyzeResponse,
    AliasMiningProposalItem,
)

_FEEDBACK_COL = "feedback"
_ALIAS_PROPOSALS_COL = "alias_mining_proposals"


class AliasMiningService:
    def __init__(self, mongo: MongoClientManager, keyword_map: dict[str, str]) -> None:
        self._mongo = mongo
        self._keyword_map = keyword_map

    async def analyze(self, request: AliasMiningAnalyzeRequest) -> AliasMiningAnalyzeResponse:
        return await asyncio.get_event_loop().run_in_executor(None, self._analyze_sync, request)

    def _analyze_sync(self, request: AliasMiningAnalyzeRequest) -> AliasMiningAnalyzeResponse:
        db = self._mongo.get_sync_db()

        feedback_col = db[_FEEDBACK_COL]
        proposals_col = db[_ALIAS_PROPOSALS_COL]

        correct_feedback = list(feedback_col.find({"action": str(FeedbackAction.CORRECT)}))
        total_feedback = len(correct_feedback)

        keyword_corrections = self._extract_keyword_patterns(correct_feedback)

        proposals = self._generate_proposals(
            keyword_corrections,
            min_frequency=request.min_frequency,
            min_confidence=request.min_confidence,
            limit=request.limit,
        )

        for proposal in proposals:
            proposals_col.insert_one(proposal.model_dump(by_alias=True))

        proposal_items = [
            AliasMiningProposalItem(
                id=p.id,
                proposal_type=str(p.proposal_type),
                status=str(p.status),
                base_color=p.base_color,
                keyword=p.keyword,
                suggested_base_color=p.suggested_base_color,
                frequency=p.frequency,
                confidence=p.confidence,
                rationale=p.rationale,
                estimated_impact=p.estimated_impact,
                created_at=p.created_at.isoformat(),
            )
            for p in proposals
        ]

        return AliasMiningAnalyzeResponse(
            status="ok",
            proposals_generated=len(proposals),
            total_feedback_analyzed=total_feedback,
            proposals=proposal_items,
        )

    def _extract_keyword_patterns(self, feedback_records: list[Any]) -> dict[str, KeywordCorrection]:
        """Mine feedback records for keyword correction patterns.

        Returns: {keyword: KeywordCorrection} mapping showing how often keywords appear in corrections.
        """
        patterns: dict[str, KeywordCorrection] = defaultdict(lambda: KeywordCorrection())

        for feedback in feedback_records:
            original_impression = feedback.get("original_impression_name", "")
            suggested_impression = feedback.get("suggested_impression_name", "")
            feedback_id = str(feedback.get("_id", ""))

            if not original_impression or not suggested_impression:
                continue

            original_tokens = set(tokenize(original_impression))
            suggested_tokens = set(tokenize(suggested_impression))

            original_colors = {self._keyword_map.get(t) for t in original_tokens if t in self._keyword_map}
            suggested_colors = {self._keyword_map.get(t) for t in suggested_tokens if t in self._keyword_map}

            if original_colors and suggested_colors:
                for keyword in original_tokens:
                    if keyword in self._keyword_map:
                        original_color = self._keyword_map[keyword]
                        is_problematic = original_color in original_colors and original_color not in suggested_colors

                        patterns[keyword].add_observation(
                            original_color=original_color,
                            suggested_colors=suggested_colors,
                            is_correction=is_problematic,
                            feedback_id=feedback_id,
                        )

        return patterns

    def _generate_proposals(
        self,
        keyword_corrections: dict[str, KeywordCorrection],
        min_frequency: int = 3,
        min_confidence: float = 0.60,
        limit: int | None = None,
    ) -> list[AliasMiningProposal]:
        """Generate proposals from keyword patterns.

        A proposal is generated when:
        - A keyword appears in corrections frequently
        - The corrections consistently suggest moving it to a different color
        """
        proposals: list[AliasMiningProposal] = []

        for keyword, correction in keyword_corrections.items():
            if correction.frequency < min_frequency:
                continue

            correction_confidence = correction.correction_rate
            if correction_confidence < min_confidence:
                continue

            current_color = self._keyword_map.get(keyword, "unknown")
            target_color = correction.most_common_target_color

            if not target_color or target_color == current_color:
                continue

            rationale = (
                f"Keyword '{keyword}' currently maps to '{current_color}' but appears in {correction.frequency} "
                f"correction(s) where reviewers prefer '{target_color}'. "
                f"Correction rate: {correction.correction_rate:.1%}"
            )

            impact = self._estimate_impact(keyword, current_color, target_color, correction.frequency)

            proposal = AliasMiningProposal(
                proposal_type=ProposalType.ALIAS_MOVE,
                status=ProposalStatus.PENDING,
                base_color=current_color,
                keyword=keyword,
                suggested_base_color=target_color,
                frequency=correction.frequency,
                confidence=correction.correction_rate,
                supporting_feedback_ids=correction.supporting_feedback_ids,
                rationale=rationale,
                estimated_impact=impact,
            )
            proposals.append(proposal)

        proposals.sort(key=lambda p: (p.frequency, p.confidence), reverse=True)

        if limit:
            proposals = proposals[:limit]

        return proposals

    @staticmethod
    def _estimate_impact(keyword: str, current_color: str, target_color: str, frequency: int) -> str:
        """Estimate the impact of applying this proposal."""
        if frequency >= 10:
            impact_level = "HIGH"
        elif frequency >= 5:
            impact_level = "MEDIUM"
        else:
            impact_level = "LOW"

        return (
            f"Moving '{keyword}' from '{current_color}' to '{target_color}' may "
            f"improve color matching accuracy for ~{frequency} mappings ({impact_level} impact)."
        )

    async def apply_proposal(self, proposal_id: str) -> dict[str, Any]:
        """Apply a proposal by updating alias_overrides.yaml."""
        return await asyncio.get_event_loop().run_in_executor(None, self._apply_proposal_sync, proposal_id)

    def _apply_proposal_sync(self, proposal_id: str) -> dict[str, Any]:
        db = self._mongo.get_sync_db()
        proposals_col = db[_ALIAS_PROPOSALS_COL]

        proposal_doc = proposals_col.find_one({"_id": proposal_id})
        if not proposal_doc:
            return {"status": "error", "message": f"Proposal {proposal_id} not found"}

        if proposal_doc.get("status") == str(ProposalStatus.APPLIED):
            return {"status": "error", "message": "Proposal already applied"}

        import os
        from pathlib import Path

        import yaml

        config_dir = os.environ.get("APP_CONFIG_DIR", "config")
        override_path = Path(config_dir) / "alias_overrides.yaml"

        overrides: dict = {}
        if override_path.exists():
            try:
                with open(override_path, encoding="utf-8") as f:
                    overrides = yaml.safe_load(f) or {}
            except Exception as e:
                return {"status": "error", "message": f"Failed to read overrides: {e}"}

        keyword = proposal_doc.get("keyword", "")
        target_color = proposal_doc.get("suggested_base_color", "")

        if not keyword or not target_color:
            return {"status": "error", "message": "Invalid proposal: missing keyword or target color"}

        if target_color not in overrides:
            overrides[target_color] = []

        if keyword not in overrides[target_color]:
            overrides[target_color].append(keyword)

        try:
            override_path.parent.mkdir(parents=True, exist_ok=True)
            with open(override_path, "w", encoding="utf-8") as f:
                yaml.dump(overrides, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            return {"status": "error", "message": f"Failed to write overrides: {e}"}

        proposals_col.update_one(
            {"_id": proposal_id},
            {
                "$set": {
                    "status": str(ProposalStatus.APPLIED),
                    "applied_at": __import__("datetime").datetime.now(__import__("datetime").UTC),
                }
            },
        )

        return {
            "status": "ok",
            "message": f"Proposal applied: '{keyword}' moved to '{target_color}' in alias_overrides.yaml",
        }

    async def list_proposals(self, status: str | None = None) -> dict[str, Any]:
        return await asyncio.get_event_loop().run_in_executor(None, self._list_proposals_sync, status)

    def _list_proposals_sync(self, status: str | None = None) -> dict[str, Any]:
        db = self._mongo.get_sync_db()
        proposals_col = db[_ALIAS_PROPOSALS_COL]

        query = {}
        if status:
            query["status"] = status

        proposals = list(proposals_col.find(query).sort("created_at", -1))

        items = [
            AliasMiningProposalItem(
                id=str(p.get("_id", "")),
                proposal_type=p.get("proposal_type", "ALIAS_MOVE"),
                status=p.get("status", "PENDING"),
                base_color=p.get("base_color", ""),
                keyword=p.get("keyword", ""),
                suggested_base_color=p.get("suggested_base_color"),
                frequency=p.get("frequency", 0),
                confidence=p.get("confidence", 0.0),
                rationale=p.get("rationale", ""),
                estimated_impact=p.get("estimated_impact"),
                created_at=str(p.get("created_at", "")),
            )
            for p in proposals
        ]

        return {"total": len(items), "proposals": items}


class KeywordCorrection:
    """Tracks correction patterns for a single keyword."""

    def __init__(self) -> None:
        self.frequency = 0
        self.correction_count = 0
        self.target_colors: dict[str, int] = defaultdict(int)
        self.supporting_feedback_ids: list[str] = []

    def add_observation(
        self,
        original_color: str,
        suggested_colors: set[str],
        is_correction: bool,
        feedback_id: str,
    ) -> None:
        self.frequency += 1
        if is_correction:
            self.correction_count += 1
            for color in suggested_colors:
                self.target_colors[color] += 1
            self.supporting_feedback_ids.append(feedback_id)

    @property
    def correction_rate(self) -> float:
        return self.correction_count / self.frequency if self.frequency > 0 else 0.0

    @property
    def most_common_target_color(self) -> str | None:
        if not self.target_colors:
            return None
        return max(self.target_colors.items(), key=lambda x: x[1])[0]
