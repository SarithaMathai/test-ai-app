import json
import logging
import sys

import pytest
from ai_core.logging import _LOGURU_AVAILABLE, JSONFormatter, _InterceptHandler, get_logger, setup_logging

pytestmark = pytest.mark.unit


def _make_record(msg: str, level: int = logging.INFO, name: str = "test") -> logging.LogRecord:
    return logging.LogRecord(
        name=name,
        level=level,
        pathname="",
        lineno=0,
        msg=msg,
        args=(),
        exc_info=None,
    )


# ── JSONFormatter ─────────────────────────────────────────────────────────────


def test_json_formatter_produces_valid_json():
    output = JSONFormatter().format(_make_record("hello"))
    parsed = json.loads(output)  # raises if not valid JSON
    assert parsed["message"] == "hello"


def test_json_formatter_fields():
    output = JSONFormatter().format(_make_record("test msg", name="my.module"))
    parsed = json.loads(output)
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "my.module"
    assert "timestamp" in parsed


def test_json_formatter_includes_exception():
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="caught error",
            args=(),
            exc_info=sys.exc_info(),
        )
    output = JSONFormatter().format(record)
    parsed = json.loads(output)
    assert "exception" in parsed
    assert "ValueError" in parsed["exception"]


# ── setup_logging ─────────────────────────────────────────────────────────────


def test_setup_logging_sets_level():
    setup_logging(level="WARNING", json_format=False)
    assert logging.getLogger().level == logging.WARNING
    setup_logging(level="INFO", json_format=False)  # restore


def test_setup_logging_uses_json_formatter():
    setup_logging(level="INFO", json_format=True)
    root = logging.getLogger()
    if _LOGURU_AVAILABLE:
        # loguru intercept handler — JSON serialization handled by loguru sink
        assert isinstance(root.handlers[0], _InterceptHandler)
    else:
        assert isinstance(root.handlers[0].formatter, JSONFormatter)


def test_setup_logging_clears_existing_handlers():
    setup_logging(level="INFO", json_format=False)
    setup_logging(level="INFO", json_format=False)
    assert len(logging.getLogger().handlers) == 1


# ── get_logger ────────────────────────────────────────────────────────────────


def test_get_logger_returns_named_logger():
    logger = get_logger("ai_core.test")
    assert logger.name == "ai_core.test"
    assert isinstance(logger, logging.Logger)


def test_get_logger_different_names_are_different_loggers():
    assert get_logger("a") is not get_logger("b")
