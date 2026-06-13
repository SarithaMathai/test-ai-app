"""Threshold Optimizer — Streamlit page.

Shows threshold adjustment proposals from automated analysis. Allows reviewers
to preview impact and apply changes to configuration.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from plm_tcin_mapper.ui.db import get_db

_THRESHOLD_PROPOSALS_COL = "threshold_proposals"


# ─── Data loaders ─────────────────────────────────────────────────────────────


@st.cache_data(ttl=300)
def _load_proposals(status: str | None = None) -> list[dict]:
    """Load threshold proposals, optionally filtered by status."""
    db = get_db()
    if db is None:
        return []
    try:
        query = {}
        if status:
            query["status"] = status
        docs = list(db[_THRESHOLD_PROPOSALS_COL].find(query).sort("created_at", -1))
        return docs
    except Exception:
        return []


def _confidence_color(confidence: float) -> str:
    """Get color indicator for confidence level."""
    if confidence >= 0.85:
        return "🟢"
    elif confidence >= 0.70:
        return "🟡"
    else:
        return "🔴"


# ─── Render functions ─────────────────────────────────────────────────────────


def render():
    """Main page rendering function."""
    st.title("⚙️ Threshold Optimizer")
    st.markdown("Automated analysis of evaluation metrics recommending configuration improvements.")

    # Tab selector
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "🔍 Pending Analysis",
            "📋 Pending Review",
            "✅ Applied",
            "❌ Rejected",
        ]
    )

    with tab1:
        _render_pending_analysis()

    with tab2:
        _render_pending_review()

    with tab3:
        _render_applied_proposals()

    with tab4:
        _render_rejected_proposals()


def _render_pending_analysis():
    """Render interface for running analysis."""
    st.subheader("Generate Proposals")
    st.markdown("Analyze the latest evaluation run to generate threshold adjustment proposals.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "🔍 Analyze Latest Evaluation",
            use_container_width=True,
            key="run_analysis",
        ):
            st.info("Running analysis... (in production, call POST /api/v1/threshold-tuning/analyze)")
            st.cache_data.clear()

    with col2:
        st.caption("Scans evaluation metrics for optimization opportunities")

    st.divider()

    st.subheader("Proposal Types")
    st.markdown(
        """
        The system automatically generates proposals for:

        **RAISE_AUTO_CONFIRM_THRESHOLD** — When correction rate is high
        - Makes algorithm more conservative
        - Reduces auto-confirmed mappings
        - Forces manual review of edge cases

        **RAISE_LLM_FALLBACK_THRESHOLD** — When HIGH confidence % is low
        - Triggers LLM for more cases
        - Improves confidence distribution
        - May increase latency slightly

        **ADJUST_LLM_FALLBACK** — Based on LLM performance
        - Lower if LLM is very accurate (correction rate < 15%)
        - Raise if LLM is causing problems (correction rate > 20%)

        **REDUCE_FUZZY_WEIGHT** — When fuzzy matching is weak signal
        - Deprioritizes fuzzy fallback
        - Relies more on token/keyword signals
        - Improves accuracy for ambiguous cases

        **ENABLE_CONFIDENCE_RECALIBRATION** — When scores don't match reality
        - Rescales confidence scores
        - Improves calibration (ECE < 0.10)
        - Enables more confident thresholds
        """
    )


def _render_pending_review():
    """Render proposals awaiting human review."""
    proposals = _load_proposals("PENDING")

    st.subheader("Pending Review")
    st.markdown("These proposals are ready for human review. Click to see details and preview impact.")

    if not proposals:
        st.info("No pending proposals. Run analysis to generate recommendations.")
        return

    # Summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Pending Proposals", len(proposals))
    with col2:
        avg_confidence = sum(p.get("confidence", 0) for p in proposals) / len(proposals) if proposals else 0
        st.metric("Avg Confidence", f"{avg_confidence:.0%}")
    with col3:
        high_confidence = sum(1 for p in proposals if p.get("confidence", 0) >= 0.80)
        st.metric("High Confidence", high_confidence)

    st.divider()

    # Proposals list
    for idx, proposal in enumerate(proposals):
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])

            with col1:
                proposal_type = proposal.get("proposal_type", "UNKNOWN")
                confidence = proposal.get("confidence", 0.0)

                st.markdown(f"{_confidence_color(confidence)} **{proposal_type}** (Confidence: {confidence:.0%})")
                st.caption(proposal.get("rationale", ""))

            with col2:
                st.metric("Type", proposal_type.split("_")[0])

            st.divider()

            # Show changes
            st.subheader("Configuration Changes")
            changes = proposal.get("changes", [])

            change_data = []
            for change in changes:
                change_data.append(
                    {
                        "Parameter": change.get("parameter", ""),
                        "Current": f"{change.get('current_value', 0):.4f}",
                        "Proposed": f"{change.get('proposed_value', 0):.4f}",
                        "Delta": f"{change.get('delta', 0):+.4f}",
                    }
                )

            if change_data:
                df = pd.DataFrame(change_data)
                st.dataframe(df, use_container_width=True)

            # Show estimated impact
            st.subheader("Estimated Impact")
            impact = proposal.get("estimated_impact", [])

            impact_data = []
            for item in impact:
                impact_data.append(
                    {
                        "Metric": item.get("metric", ""),
                        "Current": f"{item.get('current_value', 0):.4f}",
                        "Estimated": f"{item.get('estimated_value', 0):.4f}",
                        "Improvement": f"{item.get('improvement', 0):+.4f}",
                    }
                )

            if impact_data:
                df = pd.DataFrame(impact_data)

                col1, col2 = st.columns([2, 1])
                with col1:
                    st.dataframe(df, use_container_width=True)

                with col2:
                    total_improvement = sum(item.get("improvement", 0) for item in impact)
                    st.metric(
                        "Total Improvement",
                        f"{total_improvement:+.4f}",
                        delta="✅ Positive" if total_improvement > 0 else "❌ Negative",
                    )

            # Show supporting metrics
            supporting = proposal.get("supporting_metrics", {})
            if supporting:
                with st.expander("📊 Supporting Metrics"):
                    for metric, value in supporting.items():
                        st.metric(metric, f"{value:.4f}")

            # Action buttons
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button(
                    "✅ Approve",
                    key=f"approve_{idx}_{proposal.get('_id', idx)}",
                    use_container_width=True,
                ):
                    _approve_proposal(proposal)
                    st.success("Proposal approved!")
                    st.cache_data.clear()

            with col2:
                if st.button(
                    "➡️ Apply Now",
                    key=f"apply_{idx}_{proposal.get('_id', idx)}",
                    use_container_width=True,
                ):
                    _apply_proposal(proposal)

            with col3:
                if st.button(
                    "❌ Reject",
                    key=f"reject_{idx}_{proposal.get('_id', idx)}",
                    use_container_width=True,
                ):
                    _reject_proposal(proposal)
                    st.warning("Proposal rejected.")
                    st.cache_data.clear()


def _render_applied_proposals():
    """Render applied proposals and their actual results."""
    applied = _load_proposals("APPLIED")

    st.subheader("Applied Proposals")

    if not applied:
        st.info("No applied proposals yet.")
        return

    st.metric("Total Applied", len(applied))
    st.divider()

    for proposal in applied:
        with st.container(border=True):
            proposal_type = proposal.get("proposal_type", "UNKNOWN")
            applied_at = proposal.get("applied_at", "Unknown")

            st.markdown(f"✅ **{proposal_type}** — Applied at {applied_at}")

            changes = proposal.get("changes", [])
            for change in changes:
                param = change.get("parameter", "")
                current = change.get("current_value", 0)
                proposed = change.get("proposed_value", 0)

                st.markdown(f"• `{param}`: `{current:.4f}` → `{proposed:.4f}`")

            # Show actual results if available
            actual = proposal.get("actual_results", {})
            if actual:
                st.subheader("Actual Results")
                st.caption("Measured after applying proposal and running new evaluation")

                for metric, value in actual.items():
                    st.metric(metric, f"{value:.4f}")


def _render_rejected_proposals():
    """Render rejected proposals."""
    rejected = _load_proposals("REJECTED")

    st.subheader("Rejected Proposals")

    if not rejected:
        st.info("No rejected proposals yet.")
        return

    st.metric("Total Rejected", len(rejected))
    st.divider()

    for proposal in rejected:
        proposal_type = proposal.get("proposal_type", "UNKNOWN")
        confidence = proposal.get("confidence", 0.0)

        st.markdown(f"❌ **{proposal_type}** (Confidence: {confidence:.0%})")
        st.caption(proposal.get("rationale", ""))


# ─── Helper functions ─────────────────────────────────────────────────────────


def _approve_proposal(proposal: dict[str, Any]) -> None:
    """Mark a proposal as approved."""
    db = get_db()
    if db is None:
        st.error("Database connection failed")
        return

    try:
        db[_THRESHOLD_PROPOSALS_COL].update_one(
            {"_id": proposal.get("_id")},
            {"$set": {"status": "APPROVED"}},
        )
    except Exception as e:
        st.error(f"Failed to approve proposal: {e}")


def _apply_proposal(proposal: dict[str, Any]) -> None:
    """Apply a proposal to the configuration."""
    db = get_db()
    if db is None:
        st.error("Database connection failed")
        return

    try:
        import os
        from datetime import UTC, datetime
        from pathlib import Path

        import yaml

        config_dir = os.environ.get("APP_CONFIG_DIR", "config")
        config_path = Path(config_dir) / "base.yaml"

        if not config_path.exists():
            st.error(f"Configuration file not found: {config_path}")
            return

        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        changes = proposal.get("changes", [])
        for change in changes:
            param = change.get("parameter", "")
            proposed_value = change.get("proposed_value")

            if param.startswith("auto_confirm"):
                config.setdefault("matching", {})["auto_confirm_threshold"] = proposed_value
            elif param.startswith("llm_fallback"):
                config.setdefault("matching", {})["llm_fallback_threshold"] = proposed_value
            elif param.startswith("fuzzy"):
                config.setdefault("scorer", {})["fuzzy_match_weight"] = proposed_value
            elif param.startswith("confidence"):
                config.setdefault("matching", {})["enable_confidence_recalibration"] = bool(proposed_value)

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            st.error(f"Failed to write configuration: {e}")
            return

        db[_THRESHOLD_PROPOSALS_COL].update_one(
            {"_id": proposal.get("_id")},
            {
                "$set": {
                    "status": "APPLIED",
                    "applied_at": datetime.now(UTC),
                }
            },
        )

        st.success(f"✅ Applied: {len(changes)} configuration changes made")
        st.info("Changes will take effect in the next matching run (no restart needed).")
        st.cache_data.clear()

    except Exception as e:
        st.error(f"Failed to apply proposal: {e}")


def _reject_proposal(proposal: dict[str, Any]) -> None:
    """Mark a proposal as rejected."""
    db = get_db()
    if db is None:
        st.error("Database connection failed")
        return

    try:
        db[_THRESHOLD_PROPOSALS_COL].update_one(
            {"_id": proposal.get("_id")},
            {"$set": {"status": "REJECTED"}},
        )
    except Exception as e:
        st.error(f"Failed to reject proposal: {e}")
