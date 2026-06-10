"""Chat service — wraps the LLM client with prompt template logic.

Apps define prompt templates per operation (e.g. "summarise", "classify").
The service resolves the template, builds the ChatRequest, calls the LLM,
and returns the parsed result.

Adding a new operation:
  1. Add an entry to PROMPT_TEMPLATES below.
  2. No other code changes needed — the route layer uses this service generically.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ai_core.llm.base import ChatRequest, LLMClient

log = logging.getLogger(__name__)

# ── Prompt templates ──────────────────────────────────────────────────────────
# Each entry defines the system prompt and whether the response should be JSON.
# The user message is always json.dumps(payload) so structured data passes cleanly.

PROMPT_TEMPLATES: dict[str, dict[str, Any]] = {
    "summarise": {
        "system": (
            "You are a concise summarisation assistant. "
            "Summarise the user's input in 2-3 sentences. "
            "Respond in plain text."
        ),
        "response_format": "text",
    },
    "classify": {
        "system": (
            "You are a classification assistant. "
            "Classify the user's input and return a JSON object with keys: "
            "'label' (string) and 'confidence' (float 0-1). "
            "Respond ONLY with valid JSON."
        ),
        "response_format": "json",
    },
    "extract": {
        "system": (
            "You are an information extraction assistant. "
            "Extract the requested information from the input and return it as JSON. "
            "Respond ONLY with valid JSON."
        ),
        "response_format": "json",
    },
    "chat": {
        "system": "You are a helpful assistant.",
        "response_format": "text",
    },
}


class ChatService:
    """Orchestrates prompt template resolution and LLM calls."""

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
        """Execute an operation against the configured LLM.

        Returns a dict with keys: result, model, prompt_tokens, completion_tokens.
        Raises AIError on LLM failure.
        """
        template = PROMPT_TEMPLATES.get(operation)
        if template is None:
            raise ValueError(
                f"Unknown operation '{operation}'. Valid: {', '.join(PROMPT_TEMPLATES)}"
            )

        system_prompt: str = template["system"]
        response_format: str = template.get("response_format", "text")

        user_content = (
            json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload
        )

        request = ChatRequest(
            messages=[
                self._client.system(system_prompt),
                self._client.user(user_content),
            ],
            response_format=response_format,
            model=model or "",
            temperature=temperature,
            max_tokens=max_tokens,
        )

        log.info("ChatService.execute: operation=%s provider=%s", operation, self._client.provider)
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
