"""Logging configuration for PLM AI services.

Provides:
  - TAP-compatible JSON output in non-local environments (structured logging
    compatible with Target's log aggregation pipeline).
  - Colorized, human-readable output in local development.
  - Stdlib `logging` → loguru bridge so third-party libraries (uvicorn, httpx,
    requests) emit through the same sink.

Usage:
    from ai_core.logging import setup_logging, get_logger
    setup_logging(level="INFO")               # call once at app startup
    log = get_logger(__name__)
    log.info("Service started")
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

# ── loguru is used for structured + pretty output ─────────────────────────────
try:
    from loguru import logger as _loguru_logger

    _LOGURU_AVAILABLE = True
except ImportError:
    _loguru_logger = None  # type: ignore[assignment]
    _LOGURU_AVAILABLE = False


# Pretty format for local development
_LOCAL_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<cyan>{name}:<bold>{function}:{line}</bold></cyan> | "
    "<level>{level: <8}</level> | "
    "<level>{message}</level>"
)


def _is_local() -> bool:
    env = os.getenv("APP_ENV", os.getenv("APP__APP__ENV", "development")).lower()
    return env in ("", "local", "dev", "development")


class _InterceptHandler(logging.Handler):
    """Forward stdlib ``logging`` records into loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        if not _LOGURU_AVAILABLE:
            return
        try:
            level: str | int = _loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1
        _loguru_logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class JSONFormatter(logging.Formatter):
    """JSON log formatter for TAP-compatible structured output."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


# Keep private alias for internal use
_JSONFormatter = JSONFormatter


def setup_logging(level: str = "INFO", json_format: bool | None = None) -> None:
    """Configure the root logger. Call once at application startup.

    Args:
        level: Log level string (INFO, DEBUG, WARNING, ERROR).
        json_format: Force JSON output (True) or plain text (False).
            Defaults to None = auto-detect from APP_ENV (_is_local() → plain, else JSON).

    - Local dev: colorized loguru output via stdout.
    - Non-local: JSON-serialized loguru output (TAP log pipeline compatible).
    - If loguru is unavailable: falls back to stdlib JSON formatter.
    """
    log_level = level.upper()
    use_json = (not _is_local()) if json_format is None else json_format

    if _LOGURU_AVAILABLE:
        _loguru_logger.remove()
        if not use_json:
            _loguru_logger.add(sys.stdout, format=_LOCAL_FORMAT, level=log_level, colorize=True)
        else:
            _loguru_logger.add(sys.stdout, level=log_level, serialize=True)

        # Route all stdlib loggers through loguru.
        logging.basicConfig(handlers=[_InterceptHandler()], level=log_level, force=True)
        for name in ("uvicorn", "uvicorn.access", "fastapi", "httpx", "requests", "urllib3"):
            logging.getLogger(name).handlers = [_InterceptHandler()]
            logging.getLogger(name).propagate = False
    else:
        # Loguru not installed — use stdlib with JSON formatter.
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            JSONFormatter() if use_json else logging.Formatter("%(asctime)s %(levelname)-8s %(name)s %(message)s")
        )
        root = logging.getLogger()
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(getattr(logging, log_level, logging.INFO))


def get_logger(name: str) -> logging.Logger:
    """Return a named stdlib logger. Works whether loguru is installed or not."""
    return logging.getLogger(name)
