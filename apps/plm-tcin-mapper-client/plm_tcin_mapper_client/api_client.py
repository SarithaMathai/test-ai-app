"""HTTP client for calling plm-tcin-mapper-api endpoints.

All Streamlit pages import from this module instead of directly accessing MongoDB.
The API_BASE_URL can be configured via environment variable.
"""

import os
from typing import Any

import httpx

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8080")
API_TIMEOUT = 60


def _get_client() -> httpx.Client:
    """Create an httpx client with configured base URL and timeout."""
    return httpx.Client(base_url=API_BASE_URL, timeout=API_TIMEOUT)


def get(path: str, **params: Any) -> dict[str, Any]:
    """Make a GET request to the API.

    Args:
        path: API endpoint path (e.g., "/api/v1/mappings")
        **params: Query parameters

    Returns:
        Parsed JSON response as dictionary

    Raises:
        httpx.HTTPError: If the request fails
    """
    with _get_client() as client:
        response = client.get(path, params=params)
        response.raise_for_status()
        return response.json()


def post(path: str, json_data: dict[str, Any] | None = None, **params: Any) -> dict[str, Any]:
    """Make a POST request to the API.

    Args:
        path: API endpoint path (e.g., "/api/v1/feedback")
        json_data: Request body as dictionary
        **params: Query parameters

    Returns:
        Parsed JSON response as dictionary

    Raises:
        httpx.HTTPError: If the request fails
    """
    with _get_client() as client:
        response = client.post(path, json=json_data, params=params)
        response.raise_for_status()
        return response.json()


# Convenience wrappers for common operations

def health() -> dict[str, Any]:
    """Check API health."""
    return get("/health")


def get_mappings(
    pid: str | None = None,
    status: str | None = None,
    department: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """Get mappings with optional filters."""
    return get("/api/v1/mappings", pid=pid, status=status, department=department, page=page, page_size=page_size)


def get_variations(pid: str) -> list[str]:
    """Get distinct impression variations for a PID."""
    result = get("/api/v1/variations", pid=pid)
    return result.get("variations", [])


def get_departments() -> list[str]:
    """Get all distinct departments."""
    result = get("/api/v1/departments")
    return result.get("departments", [])


def get_mapping_summary(department: str | None = None) -> dict[str, Any]:
    """Get department-level mapping summary."""
    return get("/api/v1/mappings/summary", department=department)


def clear_mapping(mapping_id: str) -> dict[str, Any]:
    """Clear a mapping (set status to NO_MATCH)."""
    return post(f"/api/v1/mappings/{mapping_id}/clear")


def submit_feedback(feedback: dict[str, Any]) -> dict[str, Any]:
    """Submit feedback on a mapping."""
    return post("/api/v1/feedback", json_data=feedback)


def run_mappings(request: dict[str, Any]) -> dict[str, Any]:
    """Trigger the matching pipeline."""
    return post("/api/v1/mappings/run", json_data=request)


def ingest_data(ingest_request: dict[str, Any]) -> dict[str, Any]:
    """Ingest data into the system."""
    return post("/api/v1/ingest", json_data=ingest_request)


def run_eval_detailed() -> dict[str, Any]:
    """Run detailed evaluation."""
    return post("/api/v1/eval/detailed")


def get_eval_detailed_latest() -> dict[str, Any]:
    """Get latest detailed evaluation results."""
    return get("/api/v1/eval/detailed/latest")


def get_threshold_proposals() -> list[dict[str, Any]]:
    """Get threshold tuning proposals."""
    result = get("/api/v1/threshold-tuning/proposals")
    return result.get("proposals", [])


def analyze_threshold() -> dict[str, Any]:
    """Analyze and generate threshold proposals."""
    return post("/api/v1/threshold-tuning/analyze")


def apply_threshold_proposal(proposal_id: str) -> dict[str, Any]:
    """Apply a threshold proposal."""
    return post(f"/api/v1/threshold-tuning/proposals/{proposal_id}/apply")


def get_alias_proposals() -> list[dict[str, Any]]:
    """Get alias mining proposals."""
    result = get("/api/v1/alias-mining/proposals")
    return result.get("proposals", [])


def analyze_alias_mining() -> dict[str, Any]:
    """Analyze and generate alias mining proposals."""
    return post("/api/v1/alias-mining/analyze")


def apply_alias_proposal(proposal_id: str) -> dict[str, Any]:
    """Apply an alias mining proposal."""
    return post(f"/api/v1/alias-mining/proposals/{proposal_id}/apply")


def get_llm_quality() -> dict[str, Any]:
    """Get LLM quality metrics."""
    return get("/api/v1/llm/quality")


def get_improvements(limit: int = 100, skip: int = 0) -> dict[str, Any]:
    """Get correction impact records."""
    return get("/api/v1/improvements", limit=limit, skip=skip)


def create_improvement(impact: dict[str, Any]) -> dict[str, Any]:
    """Record a new correction impact."""
    return post("/api/v1/improvements", json_data=impact)


def get_admin_stats() -> dict[str, Any]:
    """Get admin statistics."""
    return get("/api/v1/admin/stats")
