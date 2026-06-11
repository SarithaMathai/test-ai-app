"""Unit tests for MongoClientManager."""

from unittest.mock import MagicMock, patch

import pytest
from ai_core.config import MongoConfig
from ai_mongo.client import MongoClientManager


@pytest.mark.unit
class TestMongoClientManager:
    def _make_manager(self, url: str = "mongodb://localhost:27017", database: str = "test_db") -> MongoClientManager:
        return MongoClientManager(MongoConfig(url=url, database=database))

    def test_config_stored(self):
        mgr = self._make_manager()
        assert mgr._config.database == "test_db"

    def test_lazy_init_async_client(self):
        mgr = self._make_manager()
        assert mgr._async_client is None

    def test_lazy_init_sync_client(self):
        mgr = self._make_manager()
        assert mgr._sync_client is None

    @patch("ai_mongo.client.motor.AsyncIOMotorClient")
    def test_get_async_client_creates_once(self, mock_motor):
        mock_motor.return_value = MagicMock()
        mgr = self._make_manager()
        client1 = mgr.get_async_client()
        client2 = mgr.get_async_client()
        assert client1 is client2
        mock_motor.assert_called_once()

    @patch("ai_mongo.client.MongoClient")
    def test_get_sync_client_creates_once(self, mock_pymongo):
        mock_pymongo.return_value = MagicMock()
        mgr = self._make_manager()
        client1 = mgr.get_sync_client()
        client2 = mgr.get_sync_client()
        assert client1 is client2
        mock_pymongo.assert_called_once()

    @patch("ai_mongo.client.MongoClient")
    def test_close_resets_sync_client(self, mock_pymongo):
        mock_client = MagicMock()
        mock_pymongo.return_value = mock_client
        mgr = self._make_manager()
        mgr.get_sync_client()
        mgr.close()
        assert mgr._sync_client is None
        mock_client.close.assert_called_once()
