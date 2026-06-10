"""ThinkTank / Model Garden chat completion client.

Implements ai_core.llm.base.LLMClient so apps never call the ThinkTank HTTP API
directly — all auth, retry, and response parsing is encapsulated here.

ThinkTank uses an OpenAI-compatible request/response envelope. Additional
params beyond the OpenAI standard: top_p, frequency_penalty, presence_penalty,
timeout, seed.

The factory (ai_core.llm.factory.build_llm_client) instantiates this when
settings.llm.provider == "thinktank".
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ai_core.exceptions import LLMError
from ai_core.llm.base import ChatRequest, ChatResponse, LLMClient

if TYPE_CHECKING:
    from ai_core.config import Settings

log = logging.getLogger(__name__)


class ThinkTankClient(LLMClient):
    """ThinkTank Model Garden chat completion client."""

    def __init__(self, settings: Settings) -> None:
        from ai_toss_utils.http import AuthenticatedHttpClient

        self._settings = settings
        self._http = AuthenticatedHttpClient.from_settings(settings)
        self._model = settings.llm.model
        self._temperature = settings.llm.temperature
        self._max_tokens = settings.llm.max_tokens
        self._request_timeout = settings.llm.request_timeout

    # ── LLMClient interface ────────────────────────────────────────────────────

    @property
    def provider(self) -> str:
        return "thinktank"

    @property
    def model_name(self) -> str:
        return self._model

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a chat completion request to the ThinkTank Model Garden API."""
        model = request.model or self._model
        temperature = request.temperature if request.temperature is not None else self._temperature
        max_tokens = request.max_tokens or self._max_tokens

        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 1,
            "frequency_penalty": 0.5,
            "presence_penalty": 0,
            "stream": False,
            "timeout": self._request_timeout,
        }

        log.debug("ThinkTank request: model=%s messages=%d", model, len(request.messages))

        try:
            resp = self._http.call_chat_completions(payload)
        except Exception as exc:
            raise LLMError(
                f"ThinkTank API call failed: {exc}",
                provider="thinktank",
            ) from exc

        return self._parse(resp, model)

    # ── internal ───────────────────────────────────────────────────────────────

    def _parse(self, resp: dict[str, Any], requested_model: str) -> ChatResponse:
        choices = resp.get("choices", [])
        if not choices:
            raise LLMError(
                "ThinkTank returned an empty choices list",
                provider="thinktank",
            )

        choice = choices[0]
        finish_reason = choice.get("finish_reason", "")
        content = choice.get("message", {}).get("content", "").strip()
        usage = resp.get("usage", {})

        if finish_reason not in ("stop", "length", ""):
            log.warning("Unexpected ThinkTank finish_reason: %s", finish_reason)

        return ChatResponse(
            content=content,
            model=resp.get("model", requested_model),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            finish_reason=finish_reason,
            raw=resp,
        )
