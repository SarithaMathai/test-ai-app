"""Chat completions route.

POST /api/v1/chat
  Body:  PromptRequest  { operation, payload, model?, temperature?, max_tokens? }
  Returns: PromptResponse { status, operation, result, model, token counts }
"""

from __future__ import annotations

import logging

from ai_core.exceptions import AIError
from fastapi import APIRouter, HTTPException, status

from spark_think_tank_ai.dependencies import ChatServiceDep
from spark_think_tank_ai.models.schemas import PromptRequest, PromptResponse

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=PromptResponse)
async def chat(request: PromptRequest, service: ChatServiceDep) -> PromptResponse:
    """Execute a prompt operation against the configured LLM provider."""
    try:
        result = service.execute(
            operation=request.operation,
            payload=request.payload,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except ValueError as exc:
        # Unknown operation
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AIError as exc:
        log.error("LLM error for operation=%s: %s", request.operation, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM provider error: {exc.message}",
        ) from exc

    return PromptResponse(
        operation=request.operation,
        result=result["result"],
        model=result["model"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
    )
