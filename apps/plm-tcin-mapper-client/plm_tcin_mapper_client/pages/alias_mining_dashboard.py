"""Alias Mining Dashboard — Streamlit page.

Shows pending keyword proposals from alias mining analysis. Allows reviewers
to approve/reject proposals and apply them to the keyword map.
"""

from __future__ import annotations

from typing import Any

import httpx
import streamlit as st

from plm_tcin_mapper_client import api_client


# ─── Data loaders ─────────────────────────────────────────────────────────────


@st.cache_data(ttl=300)
def _load_proposals() -> list[dict]:
    """Load alias mining proposals via API."""
    try:
        result = api_client.get_alias_proposals()
        return result
    except httpx.HTTPError:
        return []


def _get_status_color(status: str) -> str:
    """Get color for status badge."""
    colors = {
        "PENDING": "🟡",
        "APPROVED": "🟢",
        "REJECTED": "🔴",
        "APPLIED": "🔵",
    }
    return colors.get(status, "⚪")


# ─── Render functions ─────────────────────────────────────────────────────────


def render():
    """Main page rendering function."""
    st.title("🔑 Alias Mining Dashboard")
    st.markdown("Review and apply keyword refinement proposals from corrected feedback.")

    # Tab selector
    tab1, tab2 = st.tabs(
        [
            "📋 Pending Proposals",
            "✅ Approved & Applied",
        ]
    )

    with tab1:
        _render_pending_proposals()

    with tab2:
        _render_approved_proposals()


def _render_pending_proposals():
    """Render pending proposals for review."""
    proposals = _load_proposals()

    st.subheader("Pending Review")
    st.markdown(
        "These proposals are ready for human review. Click on a proposal to see details and decide whether to approve."
    )

    if not proposals:
        st.info("No pending proposals. Run alias mining analysis to generate proposals.")
        st.divider()
        st.subheader("Generate Analysis")
        if st.button("🔍 Run Alias Mining Analysis", type="primary", use_container_width=True):
            with st.spinner("Running alias mining analysis…"):
                try:
                    api_client.analyze_alias_mining()
                    st.success("Analysis complete!")
                    _load_proposals.clear()
                except httpx.HTTPError as e:
                    st.error(f"Analysis failed: {e}")
        return

    # Summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Pending Proposals", len(proposals))
    with col2:
        avg_confidence = sum(p.get("confidence", 0) for p in proposals) / len(proposals) if proposals else 0
        st.metric("Avg Confidence", f"{avg_confidence:.1%}")
    with col3:
        total_impact = sum(p.get("frequency", 0) for p in proposals)
        st.metric("Total Impact (Mappings)", total_impact)

    st.divider()

    # Proposals list
    for idx, proposal in enumerate(proposals):
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                proposal_type = proposal.get("proposal_type", "UNKNOWN")
                base_color = proposal.get("base_color", "—")
                keyword = proposal.get("keyword", "—")
                suggested_color = proposal.get("suggested_base_color", "—")

                if proposal_type == "ALIAS_MOVE":
                    st.markdown(f"**Move `{keyword}` from `{base_color}` → `{suggested_color}`**")
                else:
                    st.markdown(f"**{proposal_type}: {keyword}**")

                st.caption(proposal.get("rationale", ""))

            with col2:
                st.metric("Frequency", proposal.get("frequency", 0))
                st.metric("Confidence", f"{proposal.get('confidence', 0):.1%}")

            with col3:
                impact = proposal.get("estimated_impact", "—")
                st.caption(f"**Impact**: {impact}")

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
                    "ℹ️ Details",
                    key=f"details_{proposal_id}",
                    use_container_width=True,
                ):
                    st.json(proposal)

            # Show supporting feedback
            with st.expander("📋 Supporting Feedback"):
                feedback_ids = proposal.get("supporting_feedback_ids", [])
                if feedback_ids:
                    st.markdown(f"**{len(feedback_ids)} corrections found this pattern:**")
                    for fid in feedback_ids[:5]:
                        st.code(fid, language="text")
                    if len(feedback_ids) > 5:
                        st.caption(f"... and {len(feedback_ids) - 5} more")
                else:
                    st.caption("No feedback records linked")


def _render_approved_proposals():
    """Render approved and applied proposals."""
    proposals = _load_proposals()

    applied = [p for p in proposals if p.get("status") == "APPLIED"]

    st.subheader("Applied Proposals")

    if not applied:
        st.info("No applied proposals yet.")
        return

    st.metric("Applied", len(applied))
    st.divider()

    # Show applied proposals
    for proposal in applied:
        keyword = proposal.get("keyword", "—")
        base = proposal.get("base_color", "—")
        target = proposal.get("suggested_base_color", "—")
        applied_at = proposal.get("applied_at", "Unknown")

        st.markdown(f"✅ **{keyword}** (`{base}` → `{target}`) — Applied at {applied_at}")


# ─── Helper functions ─────────────────────────────────────────────────────────


def _apply_proposal_api(proposal_id: str) -> None:
    """Apply a proposal via API."""
    try:
        with st.spinner("Applying proposal…"):
            api_client.apply_alias_proposal(proposal_id)
            st.success("✅ Proposal applied successfully!")
            st.info("Changes will take effect in the next matching run.")
            _load_proposals.clear()
    except httpx.HTTPError as e:
        st.error(f"Failed to apply proposal: {e}")
