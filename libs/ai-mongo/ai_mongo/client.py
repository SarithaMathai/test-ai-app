"""MongoDB client wrapper.

URL-first: embed credentials directly in the connection string.

  Local dev (no auth):
      MONGO__URL=mongodb://localhost:27017

  Authenticated (user:pass in URL):
      MONGO__URL=mongodb://myuser:mypassword@host:27017/mydb

  Atlas / SRV:
      MONGO__URL=mongodb+srv://user:pass@cluster.mongodb.net/mydb

Usage:
    from ai_mongo import MongoClient
    mongo = MongoClient.from_settings(settings)
    col = mongo.collection("records")
    doc = col.find_one({"_id": "abc"})
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai_core.config import Settings


class MongoClient:
    def __init__(self, url: str, database: str) -> None:
        import pymongo

        self._client: pymongo.MongoClient[Any] = pymongo.MongoClient(url)
        self._db = self._client[database]

    @classmethod
    def from_settings(cls, settings: Settings, database: str | None = None) -> MongoClient:
        """Construct from Settings.  Override database= to target a different DB."""
        cfg = settings.mongo
        return cls(url=cfg.url, database=database or cfg.database)

    def collection(self, name: str) -> Any:
        """Return a pymongo Collection for the given name."""
        return self._db[name]

    def ping(self) -> bool:
        """Return True if the MongoDB server is reachable."""
        try:
            self._client.admin.command("ping")
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Close the underlying connection pool."""
        self._client.close()
