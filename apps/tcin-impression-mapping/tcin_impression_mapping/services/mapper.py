"""MapperService — orchestrates deterministic matching + LLM fallback.

Decision flow for each MappingRequest:
  1. Run deterministic fuzzy match.
  2. Score >= auto_threshold (0.85): accept, done.
  3. Score in [llm_threshold, auto_threshold): send to LLM for disambiguation.
  4. Score < llm_threshold (0.60): mark as no_match, queue for human review.
  5. No candidates: no_match.

The LLM is called only for ambiguous cases, keeping API costs low.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from ai_core.exceptions import LLMError

from tcin_impression_mapping.matching.deterministic import find_best_match
from tcin_impression_mapping.models.schemas import (
    BatchResult,
    MappingRequest,
    MappingResult,
    MatchStrategy,
)

if TYPE_CHECKING:
    from ai_core.llm.base import LLMClient

log = logging.getLogger(__name__)

_LLM_SYSTEM_PROMPT = """\
You are a retail color matching expert. Given a TCIN color description and a list
of impression name candidates, choose the single best match.

Respond ONLY with valid JSON (no markdown):
{
  "impression_name": "<exact string from candidates>",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<one sentence explaining the match>"
}
"""


class MapperService:
    """Orchestrates TCIN → impression mapping with deterministic + LLM fallback."""

    def __init__(
        self,
        llm_client: LLMClient,
        *,
        auto_threshold: float = 0.85,
        llm_threshold: float = 0.60,
    ) -> None:
        self._llm = llm_client
        self._auto_threshold = auto_threshold
        self._llm_threshold = llm_threshold

    # ── public API ─────────────────────────────────────────────────────────────

    def map_one(self, request: MappingRequest) -> MappingResult:
        """Map a single TCIN color to an impression name."""
        if not request.candidates:
            return MappingResult(
                pid=request.pid,
                tcin_id=request.tcin_id,
                color_name=request.color_name,
                chosen_impression="",
                confidence=0.0,
                strategy=MatchStrategy.NO_MATCH,
                reasoning="No candidate impressions provided.",
            )

        det = find_best_match(
            request.color_name,
            request.color_family,
            request.candidates,
            auto_threshold=self._auto_threshold,
            min_threshold=self._llm_threshold,  # keep candidates we might route to LLM
        )

        # High-confidence deterministic match
        if det and det.score >= self._auto_threshold:
            return MappingResult(
                pid=request.pid,
                tcin_id=request.tcin_id,
                color_name=request.color_name,
                chosen_impression=det.impression,
                confidence=det.score,
                strategy=MatchStrategy.DETERMINISTIC,
                reasoning=det.reason,
            )

        # Ambiguous — try LLM
        if det and det.score >= self._llm_threshold:
            return self._llm_map(request, top_det=det)

        # Below both thresholds — no match
        return MappingResult(
            pid=request.pid,
            tcin_id=request.tcin_id,
            color_name=request.color_name,
            chosen_impression=det.impression if det else "",
            confidence=det.score if det else 0.0,
            strategy=MatchStrategy.NO_MATCH,
            reasoning=f"Best fuzzy score {det.score:.2f} below threshold."
            if det
            else "No fuzzy match.",
        )

    def map_batch(self, requests: list[MappingRequest]) -> BatchResult:
        """Map a list of requests and return a BatchResult summary."""
        summary = BatchResult(total=len(requests))
        for req in requests:
            result = self.map_one(req)
            summary.results.append(result)
            if result.strategy == MatchStrategy.DETERMINISTIC:
                summary.deterministic += 1
            elif result.strategy == MatchStrategy.LLM:
                summary.llm_assisted += 1
                summary.prompt_tokens += result.prompt_tokens
                summary.completion_tokens += result.completion_tokens
            else:
                summary.no_match += 1
            if result.needs_review:
                summary.needs_review += 1
        return summary

    # ── internal ───────────────────────────────────────────────────────────────

    def _llm_map(self, request: MappingRequest, top_det) -> MappingResult:
        candidates_str = "\n".join(f"  {i + 1}. {c}" for i, c in enumerate(request.candidates))
        user_msg = (
            f"Match this TCIN color to one impression:\n"
            f"  PID: {request.pid}\n"
            f"  Color family: {request.color_family}\n"
            f"  Color name: {request.color_name}\n"
            f"  Size: {request.size}\n"
            f"  Deterministic top match: {top_det.impression} (score {top_det.score:.2f})\n\n"
            f"Candidates ({len(request.candidates)}):\n{candidates_str}\n\n"
            f"Which impression best matches '{request.color_name}'?"
        )

        from ai_core.llm.base import ChatRequest

        llm_request = ChatRequest(
            messages=[
                self._llm.system(_LLM_SYSTEM_PROMPT),
                self._llm.user(user_msg),
            ],
            response_format="json",
        )

        try:
            resp = self._llm.chat(llm_request)
        except LLMError as exc:
            log.warning(
                "LLM mapping failed for pid=%s: %s — using deterministic fallback", request.pid, exc
            )
            return MappingResult(
                pid=request.pid,
                tcin_id=request.tcin_id,
                color_name=request.color_name,
                chosen_impression=top_det.impression,
                confidence=top_det.score * 0.8,
                strategy=MatchStrategy.DETERMINISTIC,
                reasoning=f"LLM failed ({exc}); used deterministic fallback.",
            )

        chosen, confidence, reasoning = self._parse_llm(resp.content, request.candidates, top_det)
        return MappingResult(
            pid=request.pid,
            tcin_id=request.tcin_id,
            color_name=request.color_name,
            chosen_impression=chosen,
            confidence=confidence,
            strategy=MatchStrategy.LLM,
            reasoning=reasoning,
            prompt_tokens=resp.prompt_tokens,
            completion_tokens=resp.completion_tokens,
        )

    def _parse_llm(self, raw: str, candidates: list[str], top_det) -> tuple[str, float, str]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return top_det.impression, top_det.score * 0.8, "LLM response was not valid JSON."

        chosen = data.get("impression_name", "")
        confidence = float(data.get("confidence", 0.0))
        reasoning = str(data.get("reasoning", ""))

        if chosen not in candidates:
            chosen = top_det.impression
            confidence = max(0.0, confidence - 0.20)
            reasoning = (
                f"LLM hallucinated impression; snapped to deterministic top match. {reasoning}"
            )

        return chosen, min(1.0, max(0.0, confidence)), reasoning
