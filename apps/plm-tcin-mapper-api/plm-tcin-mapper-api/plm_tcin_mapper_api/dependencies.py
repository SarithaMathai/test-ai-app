"""FastAPI dependency providers for PLM TCIN Mapper."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any

from ai_core.config import Settings, get_settings
from ai_core.llm.base import LLMClient
from ai_core.llm.factory import build_llm_client
from ai_mongo import MongoClientManager
from fastapi import Depends

from plm_tcin_mapper_api.matching.color_keywords import get_merged_keyword_map
from plm_tcin_mapper_api.pipeline.threshold_tuner import ThresholdTuner
from plm_tcin_mapper_api.services.alias_mining_service import AliasMiningService
from plm_tcin_mapper_api.services.batch_task_manager import get_batch_task_manager
from plm_tcin_mapper_api.services.eval_service import EvalService
from plm_tcin_mapper_api.services.feedback_service import FeedbackService
from plm_tcin_mapper_api.services.ingest_service import IngestionService
from plm_tcin_mapper_api.services.mapping_service import MappingService


@lru_cache(maxsize=1)
def _cached_settings() -> Settings:
    return get_settings()


@lru_cache(maxsize=1)
def _cached_llm_client() -> LLMClient:
    return build_llm_client(_cached_settings())


@lru_cache(maxsize=1)
def _cached_mongo() -> MongoClientManager:
    return MongoClientManager(_cached_settings().mongo)


def get_app_settings() -> Settings:
    return _cached_settings()


def get_llm_client() -> LLMClient:
    return _cached_llm_client()


def get_mongo() -> MongoClientManager:
    return _cached_mongo()


def get_mapping_service(
    mongo: Annotated[MongoClientManager, Depends(get_mongo)],
    llm: Annotated[LLMClient, Depends(get_llm_client)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> MappingService:
    return MappingService(mongo=mongo, llm=llm, settings=settings)


def get_ingest_service(
    mongo: Annotated[MongoClientManager, Depends(get_mongo)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> IngestionService:
    return IngestionService(mongo=mongo, settings=settings)


def get_eval_service(
    mongo: Annotated[MongoClientManager, Depends(get_mongo)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> EvalService:
    return EvalService(mongo=mongo, settings=settings)


def get_feedback_service(
    mongo: Annotated[MongoClientManager, Depends(get_mongo)],
) -> FeedbackService:
    return FeedbackService(mongo=mongo)


def get_alias_mining_service(
    mongo: Annotated[MongoClientManager, Depends(get_mongo)],
) -> AliasMiningService:
    _, keyword_to_base = get_merged_keyword_map()
    return AliasMiningService(mongo=mongo, keyword_map=keyword_to_base)


def get_threshold_tuner_service(
    mongo: Annotated[MongoClientManager, Depends(get_mongo)],
) -> ThresholdTuner:
    return ThresholdTuner(mongo=mongo)


# Type aliases for cleaner route signatures
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
LLMClientDep = Annotated[LLMClient, Depends(get_llm_client)]
MongoDep = Annotated[MongoClientManager, Depends(get_mongo)]
MappingServiceDep = Annotated[MappingService, Depends(get_mapping_service)]
IngestionServiceDep = Annotated[IngestionService, Depends(get_ingest_service)]
EvalServiceDep = Annotated[EvalService, Depends(get_eval_service)]
FeedbackServiceDep = Annotated[FeedbackService, Depends(get_feedback_service)]
AliasMiningServiceDep = Annotated[AliasMiningService, Depends(get_alias_mining_service)]
ThresholdTunerDep = Annotated[ThresholdTuner, Depends(get_threshold_tuner_service)]
BatchTaskManagerDep = Annotated[Any, Depends(lambda: get_batch_task_manager())]
