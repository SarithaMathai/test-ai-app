"""OpenAI chat completion client.

Implements ai_core.llm.base.LLMClient so the app never imports OpenAI directly.
The factory (ai_core.llm.factory.build_llm_client) instantiates this when
settings.llm.provider == "openai".

Features:
  - Exponential-backoff retry (up to settings.llm.max_retries attempts)
  - JSON response format support (passes response_format={"type":"json_object"})
  - System certificate store for corporate SSL inspection (via truststore)
  - Custom base_url support for Azure OpenAI or proxy endpoints
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any

from ai_core.exceptions import LLMError
from ai_core.llm.base import ChatRequest, ChatResponse, LLMClient

if TYPE_CHECKING:
    from ai_core.config import Settings


class OpenAIClient(LLMClient):
    """OpenAI chat completion client implementing the LLMClient ABC."""

    def __init__(self, settings: Settings) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "openai package is not installed. Add 'openai>=1.0.0' to your app's dependencies."
            ) from exc

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set. Add it to your .env file.")

        cfg = settings.llm
        oai_cfg = settings.openai

        init_kwargs: dict[str, Any] = {
            "api_key": api_key,
            "timeout": cfg.request_timeout,
        }
        if oai_cfg.base_url:
            init_kwargs["base_url"] = oai_cfg.base_url

        # Use the system certificate store so corporate SSL inspection doesn't fail.
        try:
            import ssl

            import httpx
            import truststore  # type: ignore[import]

            ssl_ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            init_kwargs["http_client"] = httpx.Client(verify=ssl_ctx)
        except Exception:
            pass  # truststore is optional; fall back to default cert bundle

        self._client = OpenAI(**init_kwargs)
        self._model = cfg.model
        self._temperature = cfg.temperature
        self._max_tokens = cfg.max_tokens
        self._max_retries = cfg.max_retries

    # ── LLMClient interface ────────────────────────────────────────────────────

    @property
    def provider(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a chat completion request with automatic retry on transient errors."""
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        model = request.model or self._model
        temperature = request.temperature if request.temperature is not None else self._temperature
        max_tokens = request.max_tokens or self._max_tokens

        call_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if request.response_format == "json":
            call_kwargs["response_format"] = {"type": "json_object"}

        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                resp = self._client.chat.completions.create(**call_kwargs)
                usage = resp.usage
                return ChatResponse(
                    content=resp.choices[0].message.content or "",
                    model=resp.model,
                    prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
                    completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
                    finish_reason=resp.choices[0].finish_reason or "",
                    raw=resp,
                )
            except Exception as exc:
                last_exc = exc
                if attempt < self._max_retries - 1:
                    time.sleep(2**attempt)  # 1 s, 2 s, 4 s …

        raise LLMError(
            f"OpenAI call failed after {self._max_retries} attempt(s): {last_exc}",
            provider="openai",
        ) from last_exc
