"""Streamlit application entry point for the TCIN Impression Mapper operator UI.

Run locally:
    make run-tcin-ui
    # or:
    uv run --group ui streamlit run apps/plm-tcin-mapper/plm_tcin_mapper/ui/streamlit_app.py

This UI reads directly from MongoDB and is intended for internal reviewers. It
is independent of the FastAPI service (which can run in parallel on :8001).
"""

import subprocess
import sys

import streamlit as st

st.set_page_config(
    page_title="TCIN Impression Mapper",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

from plm_tcin_mapper.ui.pages import (  # noqa: E402 — must come after set_page_config
    department_view,
    llm_quality,
    pid_lookup,
)

pg = st.navigation(
    {
        "": [
            st.Page(pid_lookup.render, title="Search by PID", icon=":material/search:", url_path="pid-search", default=True),
            st.Page(department_view.render, title="Department View", icon=":material/category:", url_path="dept-search"),
        ],
        "Admin": [
            st.Page(llm_quality.render, title="LLM Quality", icon=":material/psychology:", url_path="llm-quality"),
        ],
    }
)

pg.run()


def launch() -> None:
    """Entry point for the `tcin-mapper-ui` console script."""
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(__file__),
         "--server.port=8501", "--server.address=0.0.0.0"],
        check=True,
    )
