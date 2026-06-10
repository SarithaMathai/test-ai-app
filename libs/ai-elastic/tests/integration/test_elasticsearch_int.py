"""Integration test: live Elasticsearch connection via ElasticsearchClient.

Requires a running Elasticsearch instance. Skipped automatically if ES
is not reachable (uses the `elasticsearch_available` session fixture).

Set ELASTICSEARCH__URL before running:
    ELASTICSEARCH__URL=http://localhost:9200 make test-int
"""

import pytest
import yaml

pytestmark = pytest.mark.integration

_TEST_INDEX = "ai-int-test"


@pytest.fixture()
def live_settings(tmp_path):
    import os

    es_url = os.environ.get("ELASTICSEARCH__URL", "http://localhost:9200")
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        yaml.dump(
            {
                "elasticsearch": {
                    "url": es_url,
                    "verify_certs": False,
                    "username": os.environ.get("ELASTICSEARCH__USERNAME", ""),
                }
            }
        )
    )
    from ai_core.config import load_settings

    return load_settings(config_path=cfg)


def test_elasticsearch_ping(elasticsearch_available, live_settings):
    """ElasticsearchClient.ping() returns True on a live instance."""
    from ai_elastic.client import ElasticsearchClient

    client = ElasticsearchClient.from_settings(live_settings)
    assert client.ping() is True


def test_elasticsearch_index_and_get(elasticsearch_available, live_settings):
    """Round-trip: index a doc, retrieve it, then clean up."""
    import contextlib
    import time

    from ai_elastic.client import ElasticsearchClient

    client = ElasticsearchClient.from_settings(live_settings)
    doc = {"message": "integration test doc", "value": 99}
    doc_id = "ai-int-test-001"

    try:
        client.index_document(_TEST_INDEX, doc, doc_id=doc_id)
        time.sleep(0.5)  # ES refresh is async
        result = client.get_document(_TEST_INDEX, doc_id)
        assert result is not None
        assert result.get("_source", {}).get("value") == 99
    finally:
        with contextlib.suppress(Exception):
            client.delete_document(_TEST_INDEX, doc_id)
