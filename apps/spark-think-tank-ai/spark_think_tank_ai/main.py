"""Spark Think Tank AI — FastAPI application entry point.

Startup sequence:
  1. Load settings (YAML + env vars)
  2. Configure logging
  3. Build LLM client (wired via dependency injection into routes)
  4. Mount all routers

Usage:
  uv run uvicorn spark_think_tank_ai.main:app --reload   (dev)
  make run-spark                                          (convenience)
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from ai_core.config import get_settings
from ai_core.exceptions import AIError
from ai_core.logging import setup_logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from spark_think_tank_ai.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(level=settings.app.log_level)
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="Spark Think Tank AI",
        description="LLM-powered prompt execution service. "
        "Switch providers (ThinkTank / OpenAI) via config.",
        version="0.1.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(AIError)
    async def ai_error_handler(request: Request, exc: AIError) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": exc.message},
        )

    @application.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(exc)},
        )

    application.include_router(router)
    return application


app = create_app()


def start() -> None:
    """Entry point for the `spark-start` CLI script."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "spark_think_tank_ai.main:app",
        host=settings.spark.host,
        port=settings.spark.port,
        reload=False,
    )
