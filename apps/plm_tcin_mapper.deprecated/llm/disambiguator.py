"""LLM disambiguation layer — uses ai-core LLMClient interface.

Sits between the orchestrator and the configured LLM provider (ThinkTank,
OpenAI, or none). Enriches low-confidence mapping dicts with the LLM's best
impression pick and updated confidence score. Persists all LLM calls to the
llm_calls collection for auditing, cost tracking, and performance analysis.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from ai_core.llm.base import ChatMessage, ChatRequest, LLMClient
from pymongo.database import Database

from plm_tcin_mapper.database.models import LLMCallRecord

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a product color matching expert. Given a TCIN color description and a list of impression name candidates, choose the best match.

Respond with JSON only:
{
  "chosen_impression": "<name from candidates>",
  "confidence": <0.0-1.0>,
  "reasoning": "<one sentence>"
}
"""


@dataclass
class DisambiguationResult:
    chosen_impression: str
    confidence: float
    reasoning: str
    prompt_tokens: int = 0
    response_tokens: int = 0


def disambiguate_low_confidence(
    mappings: list[dict],
    cfg: Any,
    llm: LLMClient,
    db: Database | None = None,
) -> list[dict]:
    """For mappings below cfg.matching.llm_fallback_threshold, call the LLM to
    pick the best impression from the available candidates.

    Persists all LLM calls to the llm_calls collection for auditing and cost tracking.

    Returns the same list with LLM-enhanced mappings updated in-place.
    """
    threshold = getattr(cfg.matching, "llm_fallback_threshold", 0.60)

    for m in mappings:
        if m.get("used_llm") or m.get("color_confidence", 0.0) >= threshold:
            continue
        candidates = m.get("candidates", [])
        if not candidates:
            continue

        try:
            start_time = time.time()
            result = _call_llm(llm, m, candidates)
            latency_ms = int((time.time() - start_time) * 1000)

            m["matched_impression_name"] = result.chosen_impression
            m["color_confidence"] = result.confidence
            m["llm_rationale"] = result.reasoning
            m["used_llm"] = True

            # Persist LLM call metadata for auditing
            if db:
                _persist_llm_call(db, m, result, latency_ms)

        except Exception as exc:
            logger.warning("LLM disambiguation failed for pid=%s tcin=%s: %s", m.get("pid"), m.get("tcin_id"), exc)

    return mappings


def _call_llm(llm: LLMClient, m: dict, candidates: list[str]) -> DisambiguationResult:
    color_name = m.get("tcin_color_name", m.get("color_name", ""))
    color_family = m.get("tcin_color", m.get("color_family", ""))
    size = m.get("tcin_size", m.get("size", ""))

    top_match = ""
    det_candidates = m.get("color_possible_values", [])
    if det_candidates:
        first = det_candidates[0]
        if hasattr(first, "impression_name"):
            top_match = first.impression_name
        elif isinstance(first, dict):
            top_match = first.get("impression_name", "")

    user_content = (
        f"TCIN color: '{color_name}' (family: {color_family}, size: {size})\n"
        f"Deterministic top pick: '{top_match}'\n"
        f"Candidates:\n" + "\n".join(f"  - {c}" for c in candidates)
    )

    request = ChatRequest(
        messages=[
            ChatMessage(role="system", content=_SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_content),
        ],
        response_format="json",
    )

    response = llm.chat(request)

    try:
        parsed = json.loads(response.content)
        chosen = parsed.get("chosen_impression", candidates[0] if candidates else "")
        confidence = float(parsed.get("confidence", 0.0))
        reasoning = parsed.get("reasoning", "")
    except (json.JSONDecodeError, ValueError, KeyError):
        chosen = candidates[0] if candidates else ""
        confidence = 0.0
        reasoning = f"LLM parse error. Raw: {response.content[:200]}"

    return DisambiguationResult(
        chosen_impression=chosen,
        confidence=min(max(confidence, 0.0), 1.0),
        reasoning=reasoning,
        prompt_tokens=response.prompt_tokens,
        response_tokens=response.completion_tokens,
    )


def _persist_llm_call(db: Database, m: dict, result: DisambiguationResult, latency_ms: int) -> None:
    """Write LLM call metadata to the llm_calls collection for auditing and cost tracking."""
    try:
        llm_call = LLMCallRecord(
            mapping_id=m.get("_id"),
            pid=m.get("pid"),
            tcin_id=m.get("tcin_id"),
            model=m.get("llm_model", "unknown"),
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.response_tokens,
            latency_ms=latency_ms,
            cost=0.0,  # TODO: compute based on model pricing
            chosen_impression=result.chosen_impression,
            confidence=result.confidence,
            reasoning=result.reasoning,
        )
        db["llm_calls"].insert_one(llm_call.model_dump(by_alias=True))
    except Exception as exc:
        logger.warning("Failed to persist LLM call for pid=%s: %s", m.get("pid"), exc)
