"""Workspace-root pytest configuration.

Fixtures defined here are available to every test in every package.
Integration tests use `mongo_available` / `elasticsearch_available` /
`thinktank_available` to skip gracefully when services are not reachable.
"""

from __future__ import annotations

import os
import socket

import pytest
from ai_core.config import get_settings

# ── cache-clear autouse ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear the lru_cache on get_settings before and after every test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ── helpers ────────────────────────────────────────────────────────────────────


def _tcp_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if a TCP connection to host:port can be established."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# ── integration skip fixtures ──────────────────────────────────────────────────


@pytest.fixture(scope="session")
def mongo_available():
    """Skip the test if pymongo is not installed or MongoDB is not reachable."""
    try:
        import pymongo  # noqa: F401
    except ImportError:
        pytest.skip("pymongo not installed — add it to run live MongoDB tests")

    url = os.environ.get("MONGO__URL", "mongodb://localhost:27017")
    # Extract host:port from a simple mongodb://host:port URL
    try:
        hostport = url.replace("mongodb://", "").split("/")[0].split("@")[-1]
        host, _, port_str = hostport.partition(":")
        port = int(port_str) if port_str else 27017
    except Exception:
        host, port = "localhost", 27017

    if not _tcp_reachable(host, port):
        pytest.skip(f"MongoDB not reachable at {host}:{port} — set MONGO__URL to run live tests")


@pytest.fixture(scope="session")
def elasticsearch_available():
    """Skip the test if Elasticsearch is not reachable on ELASTICSEARCH__URL."""
    url = os.environ.get("ELASTICSEARCH__URL", "http://localhost:9200")
    try:
        hostport = url.split("://", 1)[-1].split("/")[0]
        host, _, port_str = hostport.partition(":")
        port = int(port_str) if port_str else 9200
    except Exception:
        host, port = "localhost", 9200

    if not _tcp_reachable(host, port):
        pytest.skip(
            f"Elasticsearch not reachable at {host}:{port} — set ELASTICSEARCH__URL to run live tests"
        )


@pytest.fixture(scope="session")
def thinktank_available():
    """Skip the test if no ThinkTank credentials are configured."""
    has_api_key = bool(os.environ.get("THINKTANK_API_KEY"))
    has_oauth = bool(
        os.environ.get("THINKTANK_OAUTH_CLIENT_ID")
        and os.environ.get("THINKTANK_OAUTH_CLIENT_SECRET")
    )
    if not (has_api_key or has_oauth):
        pytest.skip(
            "No ThinkTank credentials found. "
            "Set THINKTANK_API_KEY or THINKTANK_OAUTH_CLIENT_ID + "
            "THINKTANK_OAUTH_CLIENT_SECRET to run live tests."
        )
