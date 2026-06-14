"""PLM TCIN Impression Mapper — FastAPI application entry point.

Exposes the deterministic + LLM matching pipeline as a REST API.

Usage (dev):
  uv run uvicorn plm_tcin_mapper.main:app --reload   (dev, port 8001)
  make run-tcin-mapper                                (convenience)
"""

from __future__ import annotations

import logging
import traceback
from contextlib import asynccontextmanager

from ai_core.config import get_settings
from ai_core.exceptions import AIError, MongoError
from ai_core.logging import setup_logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from plm_tcin_mapper_api.routes import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(level=settings.app.log_level)
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="PLM TCIN Impression Mapper",
        description="Deterministic + LLM matching pipeline that maps design impressions to guest-facing TCIN color records.",
        version="0.1.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(MongoError)
    async def mongo_error_handler(request: Request, exc: MongoError) -> JSONResponse:
        logger.error(
            "MongoError on %s %s: %s",
            request.method,
            request.url.path,
            exc.message,
        )
        return JSONResponse(status_code=503, content={"detail": exc.message})

    @application.exception_handler(AIError)
    async def ai_error_handler(request: Request, exc: AIError) -> JSONResponse:
        logger.error(
            "AIError on %s %s: %s",
            request.method,
            request.url.path,
            exc.message,
        )
        return JSONResponse(status_code=502, content={"detail": exc.message})

    @application.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        tb = traceback.format_exc()
        logger.error(
            "Unhandled exception on %s %s\n%s",
            request.method,
            request.url.path,
            tb,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": f"{type(exc).__name__}: {exc}"},
        )

    application.include_router(router)
    return application


app = create_app()


def start() -> None:
    """Entry point for the `tcin-mapper-start` CLI script."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "plm_tcin_mapper.main:app",
        host=settings.spark.host,
        port=settings.spark.port,
        reload=False,
    )
