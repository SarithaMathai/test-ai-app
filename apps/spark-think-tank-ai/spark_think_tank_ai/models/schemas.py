"""Pydantic request/response schemas for the Spark Think Tank AI API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PromptRequest(BaseModel):
    """Request body for POST /api/v1/chat."""

    operation: str = Field(
        ...,
        description="Operation name that maps to a prompt template (e.g. 'summarise', 'classify').",
        examples=["summarise"],
    )
    payload: Any = Field(
        ...,
        description="Free-form payload sent to the LLM as the user message.",
    )
    # Optional per-request overrides
    model: str | None = Field(default=None, description="Override the configured LLM model.")
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)


class PromptResponse(BaseModel):
    """Response envelope for POST /api/v1/chat."""

    status: str = Field(default="success")
    operation: str
    result: Any = Field(default=None)
    model: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str = "ok"
    provider: str | None = None
    model: str | None = None
