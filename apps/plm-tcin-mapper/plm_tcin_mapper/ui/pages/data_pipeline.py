"""Data Pipeline — ingest data and run mapping from the UI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from plm_tcin_mapper.ui.db import get_db


def render():
    st.header("Data Pipeline")
    st.caption("Load CSV data and run the matching pipeline from the UI.")

    db = get_db()
    if db is None:
        st.error("Database connection required. Please check MongoDB availability.")
        return

    tab1, tab2 = st.tabs(["📥 Ingest Data", "🔄 Run Mapping"])

    with tab1:
        _render_ingest_tab(db)

    with tab2:
        _render_mapping_tab(db)


def _render_ingest_tab(db):
    """Render data ingestion UI."""
    st.subheader("Ingest CSV Data")
    st.markdown(
        "Point to a directory containing normalized CSV files (tcin.csv, variation.csv) "
        "and load them into MongoDB."
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        data_dir = st.text_input(
            "Data directory path",
            value="./apps/plm-tcin-mapper/data/normalized",
            help="Relative or absolute path to data folder",
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        skip_existing = st.checkbox("Skip existing", value=False, help="Skip files already in MongoDB")

    if st.button("▶ Run Ingestion", type="primary", use_container_width=False):
        data_path = Path(data_dir)
        if not data_path.exists():
            st.error(f"❌ Path not found: {data_dir}")
        else:
            with st.spinner("Ingesting data…"):
                try:
                    # Import here to avoid circular dependencies
                    from plm_tcin_mapper.pipeline.ingestion import ingest_directory

                    stats = ingest_directory(str(data_path), db, skip_existing=skip_existing)

                    st.success(f"✅ Ingestion complete!")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("TCIN Records", f"{stats.get('tcin_inserted', 0) + stats.get('tcin_updated', 0):,}")
                    with col2:
                        st.metric("Variation Records", f"{stats.get('variation_inserted', 0) + stats.get('variation_updated', 0):,}")
                    with col3:
                        st.metric("Skipped", f"{stats.get('skipped', 0):,}")
                    with col4:
                        st.metric("Errors", f"{stats.get('errored', 0):,}")

                except ImportError:
                    st.error("Ingestion service not available. Run from CLI: `uv run ingest`")
                except Exception as e:
                    st.error(f"Ingestion failed: {e}")


def _render_mapping_tab(db):
    """Render mapping pipeline UI."""
    st.subheader("Run Matching Pipeline")
    st.markdown("Generate or update mappings for PIDs in the database.")

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
                from plm_tcin_mapper.pipeline.orchestrator import run_matching_pipeline

                stats = run_matching_pipeline(
                    db=db,
                    pid_filter=pid_filter.upper() if pid_filter else None,
                    department_filter=dept_filter if dept_filter else None,
                    dry_run=dry_run,
                )

                if not dry_run:
                    st.success("✅ Matching complete!")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("PIDs Processed", f"{stats.get('pids_processed', 0):,}")
                    with col2:
                        st.metric("Mappings Created", f"{stats.get('mappings_created', 0):,}")
                    with col3:
                        st.metric("AUTO_CONFIRM", f"{stats.get('auto_confirm', 0):,}")
                    with col4:
                        st.metric("NEEDS_REVIEW", f"{stats.get('needs_review', 0):,}")
                else:
                    st.info("🔍 Dry run complete (no changes saved)")

            except ImportError:
                st.error("Matching service not available. Run from CLI: `uv run run-mapping`")
            except Exception as e:
                st.error(f"Mapping failed: {e}")

    st.divider()

    st.info(
        "**Note:** The matching pipeline can also be run from the command line:\n"
        "```\nuv run run-mapping [--pid PID-XXXXX] [--department 214] [--dry-run]\n```"
    )
