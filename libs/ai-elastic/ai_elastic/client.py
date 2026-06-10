"""Elasticsearch client wrapper.

Wraps the official elasticsearch-py client with:
  - Connection built from ai-core Settings (url, username from config;
    password injected from ELASTICSEARCH__PASSWORD env var)
  - Consistent error wrapping into ElasticsearchError
  - Per-app index name injection (apps pass index names at call time)

Usage:
    from ai_elastic import ElasticsearchClient
    es = ElasticsearchClient.from_settings(settings)
    hits = es.search("my-index", {"match": {"field": "value"}})
    es.index_document("my-index", {"key": "val"}, doc_id="abc123")
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from ai_core.exceptions import ElasticsearchError

if TYPE_CHECKING:
    from ai_core.config import Settings


class ElasticsearchClient:
    def __init__(
        self,
        url: str,
        username: str = "",
        password: str = "",
        verify_certs: bool = True,
        request_timeout: int = 30,
        max_retries: int = 3,
    ) -> None:
        from elasticsearch import Elasticsearch

        kwargs: dict[str, Any] = {
            "request_timeout": request_timeout,
            "retry_on_timeout": True,
            "max_retries": max_retries,
            "verify_certs": verify_certs,
        }
        if username and password:
            kwargs["basic_auth"] = (username, password)

        self._es = Elasticsearch(url, **kwargs)

    @classmethod
    def from_settings(cls, settings: Settings) -> ElasticsearchClient:
        """Construct from Settings; password from ELASTICSEARCH__PASSWORD env var."""
        cfg = settings.elasticsearch
        password = os.environ.get("ELASTICSEARCH__PASSWORD", "")
        return cls(
            url=cfg.url,
            username=cfg.username,
            password=password,
            verify_certs=cfg.verify_certs,
            request_timeout=cfg.request_timeout,
            max_retries=cfg.max_retries,
        )

    def search(
        self,
        index: str,
        query: dict[str, Any],
        size: int = 10,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run a query against index. Returns the full ES response body."""
        try:
            resp = self._es.search(index=index, query=query, size=size, **kwargs)
            return resp.body
        except Exception as exc:
            raise ElasticsearchError(f"Search failed on index '{index}': {exc}") from exc

    def index_document(
        self,
        index: str,
        document: dict[str, Any],
        doc_id: str | None = None,
    ) -> dict[str, Any]:
        """Index a document. Returns the ES response body."""
        try:
            resp = self._es.index(index=index, body=document, id=doc_id)
            return resp.body
        except Exception as exc:
            raise ElasticsearchError(f"Index failed on '{index}': {exc}") from exc

    def get_document(self, index: str, doc_id: str) -> dict[str, Any]:
        """Fetch a document by ID."""
        try:
            resp = self._es.get(index=index, id=doc_id)
            return resp.body
        except Exception as exc:
            raise ElasticsearchError(f"Get failed — index='{index}', id='{doc_id}': {exc}") from exc

    def delete_document(self, index: str, doc_id: str) -> dict[str, Any]:
        """Delete a document by ID."""
        try:
            resp = self._es.delete(index=index, id=doc_id)
            return resp.body
        except Exception as exc:
            raise ElasticsearchError(
                f"Delete failed — index='{index}', id='{doc_id}': {exc}"
            ) from exc

    def ping(self) -> bool:
        """Return True if the cluster is reachable."""
        try:
            return bool(self._es.ping())
        except Exception:
            return False
