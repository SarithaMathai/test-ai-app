"""Data Pipeline — ingest data and run mapping from the UI."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import streamlit as st

from plm_tcin_mapper_client import api_client


def render():
    st.header("Data Pipeline")
    st.caption("Load CSV data and run the matching pipeline from the UI.")

    tab1, tab2 = st.tabs(["📥 Ingest Data", "🔄 Run Mapping"])

    with tab1:
        _render_ingest_tab()

    with tab2:
        _render_mapping_tab()


def _render_ingest_tab():
    """Render data ingestion UI."""
    st.subheader("Ingest CSV Data")
    st.markdown(
        "Provide the chunk folder path that contains both tcin.csv and variation.csv "
        "and load them into MongoDB through the API service."
    )

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        data_dir = st.text_input(
            "Chunk folder path",
            value="./apps/plm-tcin-mapper/data/normalized/chunk_01",
            help="Relative or absolute path to a chunk folder containing tcin.csv and variation.csv",
        )
    with col2:
        skip_existing = st.checkbox("Skip existing", value=False, help="Skip files already in MongoDB")

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)

    col4, col5 = st.columns(2)
    with col4:
        async_mode = st.checkbox("Async mode (fire-and-forget)", value=True)
    with col5:
        dry_run = st.checkbox("Dry run", value=False, help="Validate ingestion without writing to MongoDB")

    if st.button("▶ Run Ingestion", type="primary", use_container_width=False):
        data_path = Path(data_dir)
        if not data_path.exists():
            st.error(f"❌ Path not found: {data_dir}")
        elif not data_path.is_dir():
            st.error(f"❌ Not a directory: {data_dir}")
        elif not (data_path / "tcin.csv").exists() or not (data_path / "variation.csv").exists():
            st.error("❌ Provide a chunk folder that contains both tcin.csv and variation.csv")
        else:
            with st.spinner("Ingesting data…"):
                try:
                    ingest_request = {
                        "data_dir": str(data_path),
                        "skip_existing": skip_existing,
                        "dry_run": dry_run,
                        "async_mode": async_mode,
                    }
                    response = api_client.ingest_data(ingest_request)

                    if response.get("accepted"):
                        st.success("✅ Ingestion accepted and running in background.")
                        st.info("Check API logs for chunk/file progress and completion totals.")
                        if response.get("message"):
                            st.caption(response.get("message"))
                    else:
                        st.success("✅ Ingestion complete!")

                    totals = response.get("totals", {})
                    m1, m2, m3, m4, m5 = st.columns(5)
                    with m1:
                        st.metric("Inserted", f"{totals.get('inserted', 0):,}")
                    with m2:
                        st.metric("Updated", f"{totals.get('updated', 0):,}")
                    with m3:
                        st.metric("Skipped", f"{totals.get('skipped', 0):,}")
                    with m4:
                        st.metric("Errors", f"{totals.get('errored', 0):,}")
                    with m5:
                        st.metric("Chunks", f"{response.get('chunks_processed', 0):,}")

                except httpx.HTTPError as e:
                    st.error(f"Ingestion failed: {e}")


def _render_mapping_tab():
    """Render mapping pipeline UI."""
    st.subheader("Run Matching Pipeline")
    st.markdown("Generate or update mappings for PIDs via the API.")

    col1, col2, col3 = st.columns(3)
    with col1:
        pid_filter = st.text_input(
            "PID filter (optional)",
            placeholder="e.g. PID-0ABC12",
            help="Leave blank to match all unmatched PIDs",
        )
    with col2:
        dept_filter = st.text_input(
            "Department filter (optional)",
            placeholder="e.g. 214",
        )
    with col3:
        dry_run = st.checkbox("Dry run", value=False, help="Test without saving to DB")

    if st.button("▶ Run Matching", type="primary", use_container_width=False):
        with st.spinner("Running matching pipeline…"):
            try:
                mapping_request = {
                    "pid_filter": pid_filter.upper() if pid_filter else None,
                    "department_filter": dept_filter if dept_filter else None,
                    "dry_run": dry_run,
                }
                response = api_client.run_mappings(mapping_request)

                if not dry_run:
                    st.success("✅ Matching complete!")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("PIDs Processed", f"{response.get('pids_processed', 0):,}")
                    with col2:
                        st.metric("Mappings Created", f"{response.get('mappings_created', 0):,}")
                    with col3:
                        st.metric("AUTO_CONFIRM", f"{response.get('auto_confirm', 0):,}")
                    with col4:
                        st.metric("NEEDS_REVIEW", f"{response.get('needs_review', 0):,}")
                else:
                    st.info("🔍 Dry run complete (no changes saved)")
                    st.json(response)

            except httpx.HTTPError as e:
                st.error(f"Matching failed: {e}")

    st.divider()

    st.info(
        "**Note:** The matching pipeline can also be run from the command line:\n"
        "```\nuv run run-mapping [--pid PID-XXXXX] [--department 214] [--dry-run]\n```"
    )
