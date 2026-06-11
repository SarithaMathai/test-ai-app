"""Shared cached MongoDB accessor for the Streamlit pages.

Streamlit is synchronous, so we use the sync (PyMongo) handle from ai-mongo's
MongoClientManager — not the async Motor client used by the FastAPI service.
The connection is cached at the app level with st.cache_resource so it is
created once per Streamlit worker process and reused across all sessions.
"""

from __future__ import annotations

import streamlit as st
from ai_core.config import get_settings
from ai_mongo import MongoClientManager
from pymongo.database import Database


@st.cache_resource(show_spinner=False)
def _cached_db() -> Database | None:
    try:
        manager = MongoClientManager(get_settings().mongo)
        db = manager.get_sync_db()
        db.command("ping")
        return db
    except Exception as exc:
        st.error(
            f"Cannot connect to MongoDB: {exc}\n\n"
            "Set APP__MONGO__URL in your .env and make sure MongoDB is reachable."
        )
        return None


def get_db() -> Database | None:
    """Return the cached sync MongoDB database handle, or None if unreachable."""
    return _cached_db()
