"""MongoDB client manager — wraps Motor (async) and PyMongo (sync).

Receives a MongoConfig from ai_core; does not load config itself.
Apps instantiate and cache this via their dependency layer.
"""

from __future__ import annotations

import motor.motor_asyncio as motor
from ai_core.config import MongoConfig
from ai_core.exceptions import MongoError
from pymongo import MongoClient
from pymongo.database import Database


class MongoClientManager:
    """Holds lazy-initialized Motor and PyMongo clients for a single MongoDB instance."""

    def __init__(self, config: MongoConfig) -> None:
        self._config = config
        self._async_client: motor.AsyncIOMotorClient | None = None
        self._sync_client: MongoClient | None = None

    # ── Async (Motor) ─────────────────────────────────────────────────────────

    def get_async_client(self) -> motor.AsyncIOMotorClient:
        if self._async_client is None:
            try:
                self._async_client = motor.AsyncIOMotorClient(
                    self._config.url,
                    serverSelectionTimeoutMS=5000,
                )
            except Exception as exc:
                raise MongoError(f"Failed to create async MongoDB client: {exc}") from exc
        return self._async_client

    def get_db(self) -> motor.AsyncIOMotorDatabase:
        return self.get_async_client()[self._config.database]

    def get_collection(self, name: str) -> motor.AsyncIOMotorCollection:
        return self.get_db()[name]

    # ── Sync (PyMongo) ────────────────────────────────────────────────────────

    def get_sync_client(self) -> MongoClient:
        if self._sync_client is None:
            try:
                self._sync_client = MongoClient(
                    self._config.url,
                    serverSelectionTimeoutMS=5000,
                )
            except Exception as exc:
                raise MongoError(f"Failed to create sync MongoDB client: {exc}") from exc
        return self._sync_client

    def get_sync_db(self) -> Database:
        return self.get_sync_client()[self._config.database]

    def get_sync_collection(self, name: str):
        return self.get_sync_db()[name]

    # ── Health ────────────────────────────────────────────────────────────────

    async def ping(self) -> bool:
        try:
            await self.get_async_client().admin.command("ping")
            return True
        except Exception:
            return False

    def ping_sync(self) -> bool:
        try:
            self.get_sync_client().admin.command("ping")
            return True
        except Exception:
            return False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def close(self) -> None:
        if self._async_client is not None:
            self._async_client.close()
            self._async_client = None
        if self._sync_client is not None:
            self._sync_client.close()
            self._sync_client = None
