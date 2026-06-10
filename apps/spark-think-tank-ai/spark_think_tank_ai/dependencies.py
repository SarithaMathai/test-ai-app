"""FastAPI dependency providers.

Using FastAPI's dependency injection keeps routes thin and makes services
easy to mock in tests — inject a fake LLMClient without touching the route.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from ai_core.config import Settings, get_settings
from ai_core.llm.base import LLMClient
from ai_core.llm.factory import build_llm_client
from fastapi import Depends

from spark_think_tank_ai.services.chat_service import ChatService


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


def get_chat_service(
    llm: Annotated[LLMClient, Depends(get_llm_client)],
) -> ChatService:
    return ChatService(llm)


# Type aliases for use in route signatures
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
LLMClientDep = Annotated[LLMClient, Depends(get_llm_client)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
