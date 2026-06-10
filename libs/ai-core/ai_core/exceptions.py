from __future__ import annotations


class AIError(Exception):
    """Base exception for all ai-* packages."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ConfigError(AIError):
    """Raised when configuration is invalid or missing."""


class AuthenticationError(AIError):
    """Raised when OAuth / API key authentication fails."""


class ProviderError(AIError):
    """Raised when an AI provider call fails."""

    def __init__(self, message: str, provider: str, code: str | None = None) -> None:
        super().__init__(message, code)
        self.provider = provider


class RetryExhaustedError(ProviderError):
    """Raised when all retry attempts for a provider are exhausted."""


class LLMError(ProviderError):
    """Raised on LLM chat completion failures (parse error, quota, bad response)."""


class ElasticsearchError(AIError):
    """Raised on Elasticsearch operation failures."""


class MongoError(AIError):
    """Raised on MongoDB operation failures."""
