"""LLM client factory.

The factory is the only place in ai-core that knows about concrete providers.
It imports them lazily so ai-core itself has no hard dependency on openai or
ai-thinktank — apps install whichever provider they actually need.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_core.exceptions import ConfigError
from ai_core.llm.base import LLMClient, NoOpLLMClient

if TYPE_CHECKING:
    from ai_core.config import Settings


def build_llm_client(settings: Settings) -> LLMClient:
    """Return the configured LLM client.

    Provider is read from settings.llm.provider. Valid values:
      - "openai"     → requires libs/ai-openai in the app's dependencies
      - "thinktank"  → requires libs/ai-thinktank in the app's dependencies
      - "none"       → NoOpLLMClient (always available, returns empty responses)

    Raises:
        ConfigError: unknown provider string, or the required lib is not installed.
    """
    provider = settings.llm.provider.strip().lower()

    if provider == "openai":
        try:
            from ai_openai.client import OpenAIClient  # type: ignore[import]
        except ImportError as exc:
            raise ConfigError(
                "Provider 'openai' requires ai-openai. "
                "Add 'ai-openai' to your app's pyproject.toml dependencies."
            ) from exc
        return OpenAIClient(settings)

    if provider == "thinktank":
        try:
            from ai_thinktank.client import ThinkTankClient  # type: ignore[import]
        except ImportError as exc:
            raise ConfigError(
                "Provider 'thinktank' requires ai-thinktank. "
                "Add 'ai-thinktank' to your app's pyproject.toml dependencies."
            ) from exc
        return ThinkTankClient(settings)

    if provider == "none":
        return NoOpLLMClient()

    raise ConfigError(f"Unknown LLM provider: '{provider}'. Valid values: openai, thinktank, none.")
