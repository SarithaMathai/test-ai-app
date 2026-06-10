"""Authenticated HTTP client for ThinkTank / Model Garden API calls.

Wraps requests with:
  - Automatic Bearer token injection (via get_bearer_token)
  - Retry with exponential backoff (via tenacity)
  - Standard headers for ThinkTank (X-TGT-APPLICATION, x-api-key, tenant-id)
  - Consistent error surfacing

Usage:
    from ai_toss_utils.http import AuthenticatedHttpClient
    client = AuthenticatedHttpClient.from_settings(settings)
    response = client.post("/gen_ai_model_requests/v1/chat/completions", data)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import requests
from ai_core.exceptions import AuthenticationError, ProviderError
from tenacity import retry, stop_after_attempt, wait_exponential

from ai_toss_utils.token import get_bearer_token

if TYPE_CHECKING:
    from ai_core.config import Settings

log = logging.getLogger(__name__)

_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)


class AuthenticatedHttpClient:
    """Stateful HTTP client that refreshes the Bearer token before each request."""

    def __init__(
        self,
        settings: Settings,
        *,
        base_url: str = "",
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self._settings = settings
        self._base_url = base_url or settings.toss.base_url
        self._extra_headers = extra_headers or {}
        self._session = requests.Session()

    @classmethod
    def from_settings(cls, settings: Settings) -> AuthenticatedHttpClient:
        return cls(settings)

    # ── public API ─────────────────────────────────────────────────────────────

    def post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """POST data to endpoint (relative to base_url). Returns parsed JSON."""
        url = f"{self._base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = self._build_headers()

        @_RETRY
        def _do() -> requests.Response:
            headers["Authorization"] = get_bearer_token(self._settings)
            resp = self._session.post(url, headers=headers, json=data)
            # Raise on 5xx so tenacity retries transient server errors.
            # 4xx are client errors — reraise immediately without retry.
            if resp.status_code >= 500:
                raise ProviderError(
                    f"HTTP {resp.status_code} from {url}",
                    provider="thinktank",
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
                provider="thinktank",
            ) from exc

        if resp.status_code != 200:
            raise ProviderError(
                f"HTTP {resp.status_code} from {url}",
                provider="thinktank",
            )

        return resp.json()

    def call_chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Call the ThinkTank chat completions endpoint."""
        return self.post(self._settings.toss.chat_endpoint, payload)

    # ── internal ───────────────────────────────────────────────────────────────

    def _build_headers(self) -> dict[str, str]:
        toss = self._settings.toss
        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if toss.app_name:
            headers["x-tgt-application"] = toss.app_name
        if toss.tenant_id:
            headers["tenant-id"] = toss.tenant_id
        headers.update(self._extra_headers)
        return headers
