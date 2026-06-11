"""LLM disambiguation layer — uses ai-core LLMClient interface.

Sits between the orchestrator and the configured LLM provider (ThinkTank,
OpenAI, or none). Enriches low-confidence mapping dicts with the LLM's best
impression pick and updated confidence score.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from ai_core.llm.base import ChatMessage, ChatRequest, LLMClient

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
) -> list[dict]:
    """For mappings below cfg.matching.llm_fallback_threshold, call the LLM to
    pick the best impression from the available candidates.

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
            result = _call_llm(llm, m, candidates)
            m["matched_impression_name"] = result.chosen_impression
            m["color_confidence"] = result.confidence
            m["llm_rationale"] = result.reasoning
            m["used_llm"] = True
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
