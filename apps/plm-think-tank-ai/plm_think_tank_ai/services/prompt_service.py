"""PLM prompt service — resolves PLM-specific prompt templates and executes LLM calls.

Adding a new PLM operation:
  1. Add an entry to plm_think_tank_ai/prompts/prompt_consts.py PROMPT_TEMPLATES.
  2. No other code changes needed — this service is generic.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ai_core.llm.base import ChatRequest, LLMClient

from plm_think_tank_ai.prompts.prompt_consts import PROMPT_TEMPLATES

log = logging.getLogger(__name__)


class PromptService:
    """Orchestrates PLM prompt template resolution and LLM calls."""

    def __init__(self, llm_client: LLMClient) -> None:
        self._client = llm_client

    def execute(
        self,
        operation: str,
        payload: Any,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Execute a PLM operation against the configured LLM.

        Returns a dict with keys: result, model, prompt_tokens, completion_tokens.
        Raises ValueError for unknown operations, AIError on LLM failure.
        """
        template = PROMPT_TEMPLATES.get(operation)
        if template is None:
            raise ValueError(f"Unknown PLM operation '{operation}'. Valid operations: {', '.join(PROMPT_TEMPLATES)}")

        system_prompt: str = template["system"]
        response_format: str = template.get("response_format", "text")
        # Template can pin a model; per-request override takes precedence.
        template_model: str = template.get("model", "")

        user_content = json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload

        request = ChatRequest(
            messages=[
                self._client.system(system_prompt),
                self._client.user(user_content),
            ],
            response_format=response_format,
            model=model or template_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        log.info("PromptService.execute: operation=%s provider=%s", operation, self._client.provider)
        response = self._client.chat(request)

        result: Any = response.content
        if response_format == "json":
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                log.warning(
                    "LLM returned non-JSON for operation '%s': %s",
                    operation,
                    response.content[:200],
                )

        return {
            "result": result,
            "model": response.model,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
        }
