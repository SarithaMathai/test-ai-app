"""FastAPI dependency providers for PLM Think Tank AI."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from ai_core.config import Settings, get_settings
from ai_core.llm.base import LLMClient
from ai_core.llm.factory import build_llm_client
from fastapi import Depends

from plm_think_tank_ai.services.prompt_service import PromptService


@lru_cache(maxsize=1)
def _cached_settings() -> Settings:
    return get_settings()


@lru_cache(maxsize=1)
def _cached_llm_client() -> LLMClient:
    return build_llm_client(_cached_settings())


def get_app_settings() -> Settings:
    return _cached_settings()


def get_llm_client() -> LLMClient:
    return _cached_llm_client()


def get_prompt_service(
    llm: Annotated[LLMClient, Depends(get_llm_client)],
) -> PromptService:
    return PromptService(llm)


# Type aliases for use in route signatures
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
LLMClientDep = Annotated[LLMClient, Depends(get_llm_client)]
PromptServiceDep = Annotated[PromptService, Depends(get_prompt_service)]
