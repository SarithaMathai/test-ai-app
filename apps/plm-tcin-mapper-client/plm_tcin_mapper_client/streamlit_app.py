"""Streamlit application entry point for the TCIN Impression Mapper operator UI.

Run locally:
    uv run --package plm-tcin-mapper-client streamlit run plm_tcin_mapper_client/streamlit_app.py

This UI calls the plm-tcin-mapper-api service via HTTP and does not access MongoDB directly.
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

from plm_tcin_mapper_client.pages import (  # noqa: E402 — must come after set_page_config
    admin,
    alias_mining_dashboard,
    data_pipeline,
    department_view,
    evaluation_metrics,
    improvement_tracker,
    llm_quality,
    pid_lookup,
    review_panel,
    threshold_optimizer,
)

pg = st.navigation(
    {
        "": [
            st.Page(
                pid_lookup.render, title="Search by PID", icon=":material/search:", url_path="pid-search", default=True
            ),
            st.Page(
                department_view.render, title="Department View", icon=":material/category:", url_path="dept-search"
            ),
            st.Page(review_panel.render, title="Review Queue", icon=":material/rate_review:", url_path="review-queue"),
        ],
        "Data": [
            st.Page(data_pipeline.render, title="Data Pipeline", icon=":material/sync:", url_path="data-pipeline"),
        ],
        "Analytics": [
            st.Page(
                evaluation_metrics.render,
                title="Evaluation Metrics",
                icon=":material/analytics:",
                url_path="evaluation-metrics",
            ),
            st.Page(
                threshold_optimizer.render,
                title="Threshold Optimizer",
                icon=":material/settings:",
                url_path="threshold-optimizer",
            ),
            st.Page(
                alias_mining_dashboard.render, title="Alias Mining", icon=":material/key:", url_path="alias-mining"
            ),
            st.Page(llm_quality.render, title="LLM Quality", icon=":material/psychology:", url_path="llm-quality"),
            st.Page(
                improvement_tracker.render,
                title="Improvement Tracker",
                icon=":material/trending_up:",
                url_path="improvements",
            ),
            st.Page(admin.render, title="System Admin", icon=":material/admin_panel_settings:", url_path="admin"),
        ],
    }
)

pg.run()


def launch() -> None:
    """Entry point for the `tcin-mapper-ui` console script."""
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(__file__), "--server.port=8501", "--server.address=0.0.0.0"],
        check=True,
    )
