"""PLM prompt execution route.

POST /api/v1/prompt
  Body:  PromptRequest  { operation, payload, model?, temperature?, max_tokens? }
  Returns: PromptResponse { status, operation, result, model, token counts }
"""

from __future__ import annotations

import logging

from ai_core.exceptions import AIError
from fastapi import APIRouter, HTTPException, status

from plm_think_tank_ai.dependencies import PromptServiceDep
from plm_think_tank_ai.models.schemas import PromptRequest, PromptResponse

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["prompts"])


@router.post("/prompt", response_model=PromptResponse)
async def execute_prompt(request: PromptRequest, service: PromptServiceDep) -> PromptResponse:
    """Execute a PLM prompt operation against the configured LLM provider."""
    try:
        result = service.execute(
            operation=request.operation,
            payload=request.payload,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except ValueError as exc:
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
