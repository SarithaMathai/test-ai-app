"""Generic authenticated HTTP client with Bearer token injection and retry.

Wraps requests with:
  - Automatic Bearer token injection (via get_bearer_token)
  - Retry with exponential backoff (via tenacity)
  - Consistent error surfacing

Each integration (ThinkTank, TOSS, Confluence, Elastic, etc.) is responsible
for building and passing its own headers at construction time.

Usage:
    from ai_core.http import AuthenticatedHttpClient
    client = AuthenticatedHttpClient(
        settings,
        base_url="https://api.example.com",
        headers={"x-app-name": "my-app", "x-api-key": "key"},
    )
    response = client.post("/endpoint", data)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from ai_core.exceptions import AuthenticationError, ProviderError
from ai_core.token import get_bearer_token

if TYPE_CHECKING:
    from ai_core.config import Settings

log = logging.getLogger(__name__)

_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)


class AuthenticatedHttpClient:
    """Generic authenticated HTTP client. Injects Bearer token and retries on 5xx.

    Callers are responsible for providing integration-specific headers at
    construction time (e.g. ThinkTank headers, TOSS headers, Confluence headers).
    """

    def __init__(
        self,
        settings: Settings,
        *,
        base_url: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._settings = settings
        self._base_url = base_url
        self._static_headers = headers or {}
        self._session = requests.Session()

    # ── public API ─────────────────────────────────────────────────────────────

    def post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """POST data to endpoint (relative to base_url). Returns parsed JSON."""
        url = f"{self._base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {"Content-Type": "application/json", **self._static_headers}

        @_RETRY
        def _do() -> requests.Response:
            headers["Authorization"] = get_bearer_token(self._settings)
            resp = self._session.post(url, headers=headers, json=data)
            # Raise on 5xx so tenacity retries transient server errors.
            # 4xx are client errors — reraise immediately without retry.
            if resp.status_code >= 500:
                raise ProviderError(
                    f"HTTP {resp.status_code} from {url}",
                    provider=self._base_url,
                )
            return resp

        try:
            resp = _do()
        except AuthenticationError:
            raise
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"HTTP POST failed after retries: {url} — {exc}",
                provider=self._base_url,
            ) from exc

        if resp.status_code != 200:
            raise ProviderError(
                f"HTTP {resp.status_code} from {url}",
                provider=self._base_url,
            )

        return resp.json()
