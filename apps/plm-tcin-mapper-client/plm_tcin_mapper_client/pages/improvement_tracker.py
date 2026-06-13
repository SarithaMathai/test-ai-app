"""Improvement Tracker — track engine changes and their impact on quality metrics."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pandas as pd
import streamlit as st

from plm_tcin_mapper_client import api_client


def render():
    st.header("Improvement Tracker")
    st.caption(
        "Track how algorithm changes (alias additions, threshold adjustments, model updates) impact overall quality."
    )

    st.info(
        "This page tracks improvements from alias mining, threshold tuning, and model updates. "
        "Run matching pipeline updates to see impact data appear here."
    )

    # Load improvements from API
    try:
        result = api_client.get_improvements(limit=20)
        improvements = result.get("improvements", [])

        if not improvements:
            st.warning("No improvement records yet. Run alias mining or threshold proposals to generate impact data.")
        else:
            st.subheader("Recent Improvements")
            for imp in improvements:
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
    except httpx.HTTPError as e:
        st.error(f"Failed to load improvements: {e}")

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
                    impact_record = {
                        "trigger_type": trigger,
                        "color_family": color_family or None,
                        "description": description,
                        "confidence_delta": 0.0,
                        "high_tier_delta": 0.0,
                        "needs_review_delta": 0,
                        "pids_affected": 0,
                        "created_at": datetime.now(UTC).isoformat(),
                    }
                    api_client.create_improvement(impact_record)
                    st.success("Improvement logged!")
                except httpx.HTTPError as e:
                    st.error(f"Failed to log: {e}")
            else:
                st.warning("Please fill in required fields.")
