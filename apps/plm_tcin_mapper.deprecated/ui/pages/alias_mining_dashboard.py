"""Alias Mining Dashboard — Streamlit page.

Shows pending keyword proposals from alias mining analysis. Allows reviewers
to approve/reject proposals and apply them to the keyword map.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from plm_tcin_mapper.ui.db import get_db

_ALIAS_PROPOSALS_COL = "alias_mining_proposals"


# ─── Data loaders ─────────────────────────────────────────────────────────────


@st.cache_data(ttl=300)
def _load_proposals(status: str | None = None) -> list[dict]:
    """Load alias mining proposals, optionally filtered by status."""
    db = get_db()
    if db is None:
        return []
    try:
        query = {}
        if status:
            query["status"] = status
        docs = list(db[_ALIAS_PROPOSALS_COL].find(query).sort("created_at", -1))
        return docs
    except Exception:
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
    tab1, tab2, tab3 = st.tabs(
        [
            "📋 Pending Proposals",
            "✅ Approved & Applied",
            "❌ Rejected Proposals",
        ]
    )

    with tab1:
        _render_pending_proposals()

    with tab2:
        _render_approved_proposals()

    with tab3:
        _render_rejected_proposals()


def _render_pending_proposals():
    """Render pending proposals for review."""
    proposals = _load_proposals("PENDING")

    st.subheader("Pending Review")
    st.markdown(
        "These proposals are ready for human review. Click on a proposal to see details and decide whether to approve."
    )

    if not proposals:
        st.info("No pending proposals. Run alias mining analysis to generate proposals.")
        return

    # Summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Pending Proposals", len(proposals))
    with col2:
        avg_confidence = sum(p.get("confidence", 0) for p in proposals) / len(proposals)
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
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button(
                    "✅ Approve",
                    key=f"approve_{idx}_{proposal.get('_id', idx)}",
                    use_container_width=True,
                ):
                    _approve_proposal(proposal)
                    st.success("Proposal approved! (Review only, not yet applied)")
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
    approved = _load_proposals("APPROVED")
    applied = _load_proposals("APPLIED")

    all_proposals = approved + applied

    st.subheader("Approved & Applied")

    if not all_proposals:
        st.info("No approved or applied proposals yet.")
        return

    # Summary
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Approved (Pending Apply)", len(approved))
    with col2:
        st.metric("Applied", len(applied))

    st.divider()

    # Show approved proposals (not yet applied)
    if approved:
        st.subheader("✅ Approved (Ready to Apply)")
        for idx, proposal in enumerate(approved):
            with st.container(border=True):
                keyword = proposal.get("keyword", "—")
                base = proposal.get("base_color", "—")
                target = proposal.get("suggested_base_color", "—")

                st.markdown(f"**{keyword}** (`{base}` → `{target}`)")
                st.caption(
                    f"Confidence: {proposal.get('confidence', 0):.1%} | Impact: {proposal.get('frequency', 0)} mappings"
                )

                if st.button(
                    "➡️ Apply to Configuration",
                    key=f"apply_approved_{idx}",
                    use_container_width=True,
                ):
                    _apply_proposal(proposal)

    # Show applied proposals
    if applied:
        st.subheader("🔵 Applied to Configuration")
        for proposal in applied:
            keyword = proposal.get("keyword", "—")
            base = proposal.get("base_color", "—")
            target = proposal.get("suggested_base_color", "—")
            applied_at = proposal.get("applied_at", "Unknown")

            st.markdown(f"✅ **{keyword}** (`{base}` → `{target}`) — Applied at {applied_at}")


def _render_rejected_proposals():
    """Render rejected proposals."""
    rejected = _load_proposals("REJECTED")

    st.subheader("❌ Rejected Proposals")

    if not rejected:
        st.info("No rejected proposals yet.")
        return

    st.metric("Total Rejected", len(rejected))
    st.divider()

    for proposal in rejected:
        keyword = proposal.get("keyword", "—")
        base = proposal.get("base_color", "—")
        target = proposal.get("suggested_base_color", "—")

        st.markdown(f"**{keyword}** (`{base}` → `{target}`)")
        st.caption(f"Confidence: {proposal.get('confidence', 0):.1%} | Frequency: {proposal.get('frequency', 0)}")


# ─── Helper functions ─────────────────────────────────────────────────────────


def _approve_proposal(proposal: dict[str, Any]) -> None:
    """Mark a proposal as approved."""
    db = get_db()
    if db is None:
        st.error("Database connection failed")
        return

    try:
        db[_ALIAS_PROPOSALS_COL].update_one(
            {"_id": proposal.get("_id")},
            {"$set": {"status": "APPROVED"}},
        )
    except Exception as e:
        st.error(f"Failed to approve proposal: {e}")


def _apply_proposal(proposal: dict[str, Any]) -> None:
    """Apply a proposal to the keyword configuration."""
    db = get_db()
    if db is None:
        st.error("Database connection failed")
        return

    try:
        keyword = proposal.get("keyword", "")
        target_color = proposal.get("suggested_base_color", "")

        if not keyword or not target_color:
            st.error("Invalid proposal: missing keyword or target color")
            return

        import os
        from pathlib import Path

        import yaml

        config_dir = os.environ.get("APP_CONFIG_DIR", "config")
        override_path = Path(config_dir) / "alias_overrides.yaml"

        overrides: dict = {}
        if override_path.exists():
            try:
                with open(override_path, encoding="utf-8") as f:
                    overrides = yaml.safe_load(f) or {}
            except Exception as e:
                st.error(f"Failed to read overrides: {e}")
                return

        if target_color not in overrides:
            overrides[target_color] = []

        if keyword not in overrides[target_color]:
            overrides[target_color].append(keyword)

        try:
            override_path.parent.mkdir(parents=True, exist_ok=True)
            with open(override_path, "w", encoding="utf-8") as f:
                yaml.dump(overrides, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            st.error(f"Failed to write overrides: {e}")
            return

        # Update proposal status in DB
        db[_ALIAS_PROPOSALS_COL].update_one(
            {"_id": proposal.get("_id")},
            {
                "$set": {
                    "status": "APPLIED",
                    "applied_at": __import__("datetime").datetime.now(__import__("datetime").UTC),
                }
            },
        )

        st.success(f"✅ Applied: '{keyword}' moved to '{target_color}'")
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
        db[_ALIAS_PROPOSALS_COL].update_one(
            {"_id": proposal.get("_id")},
            {"$set": {"status": "REJECTED"}},
        )
    except Exception as e:
        st.error(f"Failed to reject proposal: {e}")
