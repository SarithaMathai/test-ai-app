# ai-toss-utils — Developer Guide

## Auth fallback chain

Authentication logic lives in `ai_toss_utils/token.py`. The priority is:

1. `pyOauthTarget` is importable AND `toss.oauth_client_id` is set → OAuth2 client credentials.
2. `tgt-certs` is importable OR `toss.api_key` is non-empty → return `toss.api_key` as bearer.
3. Empty string (graceful degradation, not an error — only logs a warning).

Both `pyOauthTarget` and `tgt-certs` are **dynamic imports** — they are NOT listed as `[project.dependencies]`. This prevents install failures on machines that don't have access to the Target internal PyPI (`tgt-python` index).

## Modifying retry behaviour

Retry logic wraps `requests.Session.request` in `ai_toss_utils/http.py` using `tenacity`. To change:

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(requests.exceptions.ConnectionError),
)
```

## Adding a new HTTP endpoint method

Add a method on `AuthenticatedHttpClient` in `ai_toss_utils/http.py`:

```python
def call_my_endpoint(self, payload: dict) -> dict:
    url = f"{self._settings.toss.thinktank_url}/v1/my-endpoint"
    return self._post(url, payload)
```

`_post()` builds headers, serializes JSON, retries, and raises on HTTP errors.

## Running locally without TAP secrets

Set these in your `.env` file (copy from `.env.example`):

```bash
THINKTANK_API_KEY=<your-test-key>
THINKTANK_URL=https://api.thinktank.target.com
```

`get_bearer_token` will use the API key as the bearer when OAuth packages are absent.

## Testing

Unit tests mock `get_bearer_token` and the `requests.Session`:

```python
from unittest.mock import patch, MagicMock

with patch("ai_toss_utils.http.get_bearer_token", return_value="test-token"):
    with patch("requests.Session.request") as mock_req:
        mock_req.return_value = MagicMock(status_code=200, json=lambda: {"result": "ok"})
        ...
```
