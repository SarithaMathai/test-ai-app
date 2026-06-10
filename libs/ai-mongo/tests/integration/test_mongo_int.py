"""Integration test: live MongoDB connection via MongoClient.

Requires a running MongoDB instance. Skipped automatically if MongoDB
is not reachable (uses the `mongo_available` session fixture from conftest.py).

Set MONGO__URL env var to point at your instance before running:
    MONGO__URL=mongodb://user:pass@localhost:27017 make test-int
"""

import pytest
import yaml

pytestmark = pytest.mark.integration


@pytest.fixture()
def live_settings(tmp_path):
    """Settings pointed at the real MONGO__URL env var (if set)."""
    import os

    mongo_url = os.environ.get("MONGO__URL", "mongodb://localhost:27017")
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.dump({"mongo": {"url": mongo_url, "database": "ai_test_db"}}))
    from ai_core.config import load_settings

    return load_settings(config_path=cfg)


def test_mongo_ping(mongo_available, live_settings):
    """MongoClient.ping() returns True on a live instance."""
    from ai_mongo.client import MongoClient

    client = MongoClient.from_settings(live_settings)
    try:
        assert client.ping() is True
    finally:
        client.close()


def test_mongo_collection_insert_and_find(mongo_available, live_settings):
    """Round-trip: insert a doc, find it by _id, then delete it.

    Skipped gracefully when the MongoDB instance requires authentication
    (unauthenticated write operations raise OperationFailure code 13).
    Embed credentials directly in MONGO__URL: mongodb://user:pass@host:27017/db
    """
    import contextlib

    import pymongo.errors
    from ai_mongo.client import MongoClient

    client = MongoClient.from_settings(live_settings)
    col = client.collection("_ai_int_test")
    doc_id = None
    try:
        inserted = col.insert_one({"_test_key": "integration_test", "value": 42})
        doc_id = inserted.inserted_id
        assert doc_id is not None

        found = col.find_one({"_id": doc_id})
        assert found is not None
        assert found["value"] == 42
    except pymongo.errors.OperationFailure as exc:
        if exc.code == 13:  # Unauthorized
            pytest.skip(
                "MongoDB requires authentication. "
                "Embed credentials in MONGO__URL: mongodb://user:pass@host:27017/db"
            )
        raise
    finally:
        if doc_id is not None:
            with contextlib.suppress(Exception):
                col.delete_one({"_id": doc_id})
        client.close()
