"""Improvement Tracker — track engine changes and their impact on quality metrics."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from plm_tcin_mapper.ui.db import get_db


def render():
    st.header("Improvement Tracker")
    st.caption("Track how algorithm changes (alias additions, threshold adjustments, model updates) impact overall quality.")

    db = get_db()
    if db is None:
        st.error("Database not connected.")
        return

    st.info(
        "This page tracks improvements from alias mining, threshold tuning, and model updates. "
        "Run matching pipeline updates to see impact data appear here."
    )

    # Try to load correction impacts if the collection exists
    try:
        impacts = list(db.correction_impacts.find().sort("created_at", -1).limit(20))
        if not impacts:
            st.warning("No improvement records yet. Run alias mining or threshold proposals to generate impact data.")
        else:
            st.subheader("Recent Improvements")
            for imp in impacts:
                with st.expander(f"{imp.get('trigger_type', 'unknown')} — {str(imp.get('created_at', ''))[:10]}"):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Confidence Δ", f"{imp.get('confidence_delta', 0):+.3f}")
                    with col2:
                        st.metric("HIGH Tier Δ", f"{imp.get('high_tier_delta', 0):+.1%}")
                    with col3:
                        st.metric("Needs Review Δ", f"{imp.get('needs_review_delta', 0):+.0f}")
                    with col4:
                        st.metric("PIDs Affected", f"{imp.get('pids_affected', 0)}")
                    if imp.get("description"):
                        st.markdown(f"**Note:** {imp['description']}")
    except Exception:
        st.info("Correction impacts collection not yet created. It will be populated as you run matching updates.")

    st.divider()

    # Manual logging form
    st.subheader("Record a Manual Improvement")
    st.caption("Use this to manually log improvements that don't come from the automated proposal system.")

    with st.form("improvement_form"):
        trigger = st.selectbox(
            "Change Type",
            ["alias_added", "threshold_changed", "model_updated", "manual_review"],
        )
        color_family = st.text_input("Color Family (optional)", placeholder="e.g. BLUE, NEUTRAL")
        description = st.text_area("Description", placeholder="What change was made?")

        if st.form_submit_button("Log Improvement"):
            if trigger and description:
                try:
                    db.correction_impacts.insert_one({
                        "trigger_type": trigger,
                        "color_family": color_family or None,
                        "description": description,
                        "confidence_delta": 0.0,
                        "high_tier_delta": 0.0,
                        "needs_review_delta": 0,
                        "pids_affected": 0,
                        "created_at": pd.Timestamp.now(),
                    })
                    st.success("Improvement logged!")
                except Exception as e:
                    st.error(f"Failed to log: {e}")
            else:
                st.warning("Please fill in required fields.")
