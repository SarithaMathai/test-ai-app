"""Abstract LLM client interface and shared data types.

Every provider (OpenAI, ThinkTank, …) implements LLMClient.
Apps call build_llm_client(settings) and work against this interface only —
they never import a concrete client directly.

To add a new provider:
  1. Create libs/ai-<name>/ai_<name>/client.py implementing LLMClient
  2. Add a case in ai_core/llm/factory.py
  3. Set llm.provider in config/base.yaml
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatMessage:
    """A single turn in a conversation."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class ChatRequest:
    """Input to a chat completion call."""

    messages: list[ChatMessage]
    model: str = ""  # overrides settings.llm.model when set
    temperature: float | None = None  # overrides settings.llm.temperature when set
    max_tokens: int | None = None  # overrides settings.llm.max_tokens when set
    response_format: str = "text"  # "text" | "json"
    stream: bool = False
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    """Output from a chat completion call."""

    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = ""
    raw: Any = None  # provider-specific raw response object

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMClient(ABC):
    """Abstract LLM client. Implement this interface to add a new provider."""

    @abstractmethod
    def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a chat completion request and return a structured response."""
        ...

    @property
    @abstractmethod
    def provider(self) -> str:
        """Provider identifier: 'openai', 'thinktank', 'none', etc."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Active model identifier (e.g. 'gpt-4o', 'llama-3-70b')."""
        ...

    def system(self, content: str) -> ChatMessage:
        return ChatMessage(role="system", content=content)

    def user(self, content: str) -> ChatMessage:
        return ChatMessage(role="user", content=content)


class NoOpLLMClient(LLMClient):
    """Disabled LLM client. Used when llm.provider = 'none'.

    Returns empty responses so callers that check finish_reason can handle
    the disabled case without branching on provider type.
    """

    def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            content="",
            model="none",
            finish_reason="disabled",
        )

    @property
    def provider(self) -> str:
        return "none"

    @property
    def model_name(self) -> str:
        return "none"
