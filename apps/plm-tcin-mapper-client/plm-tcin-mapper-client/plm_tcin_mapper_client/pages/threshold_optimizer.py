"""Threshold Optimizer — Streamlit page.

Shows threshold adjustment proposals from automated analysis. Allows reviewers
to preview impact and apply changes to configuration.
"""

from __future__ import annotations

import httpx
import pandas as pd
import streamlit as st
from plm_tcin_mapper_client import api_client

# ─── Data loaders ─────────────────────────────────────────────────────────────


@st.cache_data(ttl=300)
def _load_proposals() -> list[dict]:
    """Load threshold proposals via API."""
    try:
        result = api_client.get_threshold_proposals()
        return result
    except httpx.HTTPError:
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
    tab1, tab2 = st.tabs(
        [
            "🔍 Pending Analysis",
            "📋 Proposals",
        ]
    )

    with tab1:
        _render_pending_analysis()

    with tab2:
        _render_proposals()


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
            with st.spinner("Running analysis…"):
                try:
                    api_client.analyze_threshold()
                    st.success("Analysis complete!")
                    _load_proposals.clear()
                except httpx.HTTPError as e:
                    st.error(f"Analysis failed: {e}")

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


def _render_proposals():
    """Render all proposals."""
    proposals = _load_proposals()

    st.subheader("Threshold Proposals")
    st.markdown("Proposals are ready for human review. Click to see details and preview impact.")

    if not proposals:
        st.info("No proposals available. Run analysis to generate recommendations.")
        return

    # Summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Proposals", len(proposals))
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
            proposal_id = str(proposal.get("id", idx))
            col1, col2 = st.columns(2)

            with col1:
                if st.button(
                    "➡️ Apply Now",
                    key=f"apply_{proposal_id}",
                    use_container_width=True,
                ):
                    _apply_proposal_api(proposal_id)

            with col2:
                if st.button(
                    "ⓘ Details",
                    key=f"details_{proposal_id}",
                    use_container_width=True,
                ):
                    st.json(proposal)


# ─── Helper functions ─────────────────────────────────────────────────────────


def _apply_proposal_api(proposal_id: str) -> None:
    """Apply a proposal via API."""
    try:
        with st.spinner("Applying proposal…"):
            api_client.apply_threshold_proposal(proposal_id)
            st.success("✅ Proposal applied successfully!")
            st.info("Changes will take effect in the next matching run.")
            _load_proposals.clear()
    except httpx.HTTPError as e:
        st.error(f"Failed to apply proposal: {e}")
