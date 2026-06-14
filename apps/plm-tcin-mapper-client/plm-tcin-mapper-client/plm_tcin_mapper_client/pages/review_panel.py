"""Review Panel — human-in-the-loop feedback queue for low-confidence mappings."""

from __future__ import annotations

import httpx
import streamlit as st
from plm_tcin_mapper_client import api_client
from plm_tcin_mapper_client.enums import FeedbackAction, MappingStatus

_TIER_ICON = {"HIGH": "🟢", "GOOD": "🔵", "FAIR": "🟡", "LOW": "🔴"}
_TIER_COLOR = {
    "HIGH": "#4CAF50",
    "GOOD": "#2196F3",
    "FAIR": "#FF9800",
    "LOW": "#F44336",
}

_REVIEW_STATUS_MAP = {
    "NO_MATCH": "NO_MATCH",
    "NEEDS_REVIEW": "NEEDS_REVIEW",
    "NEEDS_SPOT_CHECK": "NEEDS_SPOT_CHECK",
    "All Pending": None,  # None means fetch all pending statuses
}

_ROUND_ICON = {
    "GREEDY": "⚡",
    "HUNGARIAN": "🔢",
    "FALLBACK": "⚠️",
    "LLM": "🤖",
}
_ROUND_DESC = {
    "GREEDY": "High-confidence direct match (score ≥ 0.85)",
    "HUNGARIAN": "Optimal global assignment (good score, not greedy-locked)",
    "FALLBACK": "Structural mismatch — more TCIN colors than impressions; best-available impression used",
    "LLM": "LLM attempted disambiguation on a low-confidence deterministic result",
}

_STATUS_AFTER_ACTION = {
    FeedbackAction.CONFIRM: MappingStatus.CONFIRMED,
    FeedbackAction.REJECT: MappingStatus.REJECTED,
    FeedbackAction.CORRECT: MappingStatus.CORRECTED,
}


def _confidence_bar(score: float, tier: str) -> str:
    pct = int(score * 100)
    color = _TIER_COLOR.get(tier, "#9E9E9E")
    icon = _TIER_ICON.get(tier, "⚪")
    return (
        f'<div style="display:flex;align-items:center;gap:10px;margin:6px 0;">'
        f'<div style="flex:1;background:#e0e0e0;border-radius:4px;height:12px;">'
        f'<div style="background:{color};width:{pct}%;height:12px;border-radius:4px;"></div>'
        f"</div>"
        f'<strong style="white-space:nowrap;">{icon} {pct}% {tier}</strong>'
        f"</div>"
    )


def _load_queue(
    queue_type: str,
    limit: int = 100,
    match_rounds: list[str] | None = None,
) -> list[dict]:
    """Load mappings from API based on status and optional match round filters."""
    try:
        status = _REVIEW_STATUS_MAP.get(queue_type, "NEEDS_REVIEW")
        result = api_client.get_mappings(status=status, page=1, page_size=limit)
        mappings = result.get("items", [])

        # Filter by match round if specified
        if match_rounds:
            mappings = [m for m in mappings if m.get("match_round") in match_rounds]

        return mappings
    except httpx.HTTPError as e:
        st.error(f"Failed to load queue: {e}")
        return []


def _get_impression_options(pid: str) -> list[str]:
    """Return all distinct impression names for this PID."""
    try:
        variations = api_client.get_variations(pid)
        return sorted(variations)
    except httpx.HTTPError:
        return []


def _get_candidate_options(m: dict, pid: str) -> tuple[list[str], list[dict]]:
    """
    Return (ordered option list, sorted candidate dicts).
    Candidates from color_possible_values come first (sorted by score),
    then remaining impressions for the PID.
    """
    raw_cands = m.get("color_possible_values", [])
    sorted_cands = sorted(raw_cands, key=lambda x: x.get("score", 0), reverse=True)
    cand_names = [c.get("impression_name", "") for c in sorted_cands if c.get("impression_name")]

    all_impressions = _get_impression_options(pid)
    remaining = [i for i in all_impressions if i not in cand_names]
    options = cand_names + remaining
    return options, sorted_cands


def _submit_feedback(
    mapping: dict,
    action: FeedbackAction,
    reviewer: str,
    suggested_impression: str | None,
    notes: str,
) -> bool:
    """Submit feedback via API and update mapping status. Returns True on success."""
    try:
        mapping_id = str(mapping.get("id", ""))
        pid = mapping.get("pid", "")

        feedback = {
            "mapping_id": mapping_id,
            "pid": pid,
            "tcin_id": mapping.get("tcin_id", ""),
            "action": action.value,
            "reviewer": reviewer or None,
            "notes": notes or None,
            "tcin_color": mapping.get("tcin_color"),
            "tcin_color_name": mapping.get("tcin_color_name"),
            "tcin_size": mapping.get("tcin_size"),
            "department_ids": mapping.get("department_ids", []),
            "match_round": mapping.get("match_round"),
            "original_confidence_tier": mapping.get("confidence_tier"),
            "suggested_impression_name": suggested_impression or None,
            "original_impression_name": mapping.get("matched_impression_name"),
            "original_color_confidence": mapping.get("color_confidence"),
            "was_correct": (action == FeedbackAction.CONFIRM),
        }

        api_client.submit_feedback(feedback)
        return True
    except httpx.HTTPError as e:
        st.error(f"Failed to save feedback: {e}")
        return False


# ─── Outcome banner ────────────────────────────────────────────────────────────


def _render_outcome_banner(
    action_label: str,
    original_impression: str | None,
    suggested_impression: str | None,
) -> None:
    """
    Show a live banner that tells the reviewer what signal they are sending
    to the matching engine before they click Submit.
    """
    if action_label == "Confirm":
        st.markdown(
            '<div style="background:#e8f5e9;border-left:4px solid #4CAF50;'
            'padding:10px 14px;border-radius:4px;margin:8px 0;">'
            '<strong style="color:#2e7d32;">✓ Marking as CORRECT</strong> — '
            "you are teaching the engine that this match is right. "
            "This confirmation will improve signal accuracy scores for the matched signal type."
            "</div>",
            unsafe_allow_html=True,
        )
    elif action_label == "Reject":
        st.markdown(
            '<div style="background:#ffebee;border-left:4px solid #F44336;'
            'padding:10px 14px;border-radius:4px;margin:8px 0;">'
            '<strong style="color:#c62828;">✗ Marking as WRONG</strong> — '
            "you are telling the engine this match is incorrect. "
            "This rejection lowers the signal accuracy for this match type and will "
            "inform threshold proposals."
            "</div>",
            unsafe_allow_html=True,
        )
    elif action_label == "Correct":
        correct_to = suggested_impression or "_(select an impression above)_"
        original = original_impression or "_(original)_"
        st.markdown(
            '<div style="background:#fff8e1;border-left:4px solid #FF9800;'
            'padding:10px 14px;border-radius:4px;margin:8px 0;">'
            f'<strong style="color:#e65100;">✏ Marking as WRONG — providing correction</strong><br>'
            f'<span style="color:#555;">Original: <code>{original}</code> → '
            f"Correct: <code>{correct_to}</code></span><br>"
            "<small>Both the rejection and the correction are recorded. "
            "The engine mines these corrections for alias and LLM few-shot proposals.</small>"
            "</div>",
            unsafe_allow_html=True,
        )


# ─── Page ─────────────────────────────────────────────────────────────────────


def render():
    st.header("Review Queue")
    st.caption("Work through the human review queue. Each action trains the matching engine.")

    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([2, 2, 2, 1])
    with ctrl1:
        queue_type = st.selectbox(
            "Review Queue",
            options=["NO_MATCH", "NEEDS_REVIEW", "NEEDS_SPOT_CHECK", "All Pending"],
            index=0,
        )
    with ctrl2:
        reviewer = st.text_input("Your name / email", placeholder="reviewer@example.com")
    with ctrl3:
        round_filter = st.multiselect(
            "Filter by match round",
            options=["GREEDY", "HUNGARIAN", "FALLBACK", "LLM"],
            default=[],
            help="Leave empty to show all rounds.",
        )
    with ctrl4:
        st.markdown("<br>", unsafe_allow_html=True)
        reload = st.button("Load Queue", type="primary", use_container_width=True)

    st.markdown("---")

    if "review_queue" not in st.session_state or reload:
        with st.spinner("Loading review queue …"):
            st.session_state["review_queue"] = _load_queue(
                queue_type,
                limit=100,
                match_rounds=round_filter if round_filter else None,
            )
        st.session_state["review_idx"] = 0
        st.session_state["reviewed_ids"] = set()

    queue: list[dict] = st.session_state["review_queue"]
    reviewed: set = st.session_state["reviewed_ids"]
    remaining = [m for m in queue if str(m.get("id", "")) not in reviewed]

    if not remaining:
        if not queue:
            st.success("No mappings in the review queue. The system is caught up!")
        else:
            st.success(f"All {len(reviewed)} items reviewed this session. Click **Load Queue** to fetch fresh items.")
        return

    total_loaded = len(queue)
    done = len(reviewed)
    st.progress(
        done / total_loaded if total_loaded else 0,
        text=f"Reviewed {done} of {total_loaded} loaded  |  {len(remaining)} remaining",
    )

    idx = st.session_state.get("review_idx", 0)
    idx = min(idx, len(remaining) - 1)

    def _go_prev():
        st.session_state["review_idx"] = max(0, st.session_state.get("review_idx", 0) - 1)

    def _go_next():
        st.session_state["review_idx"] = min(len(remaining) - 1, st.session_state.get("review_idx", 0) + 1)

    nav_prev, nav_info, nav_next = st.columns([1, 3, 1])
    with nav_prev:
        st.button("← Prev", disabled=(idx == 0), on_click=_go_prev)
    with nav_info:
        st.markdown(
            f"<div style='text-align:center;padding:6px;'>Card <b>{idx + 1}</b> of <b>{len(remaining)}</b></div>",
            unsafe_allow_html=True,
        )
    with nav_next:
        st.button("Next →", disabled=(idx >= len(remaining) - 1), on_click=_go_next)

    st.markdown("---")

    m = remaining[idx]
    if m.get("status") == "NO_MATCH":
        _render_no_match_card(m, reviewer, reviewed)
    else:
        _render_review_card(m, reviewer, reviewed)


# ─── NO_MATCH card ─────────────────────────────────────────────────────────────


def _render_no_match_card(m: dict, reviewer: str, reviewed: set):
    """
    Card for NO_MATCH mappings — confidence was below 0.75, no impression assigned.
    User must pick from the candidate dropdown and click Assign.
    """
    tier = m.get("confidence_tier", "LOW")
    score = m.get("color_confidence", 0.0)
    pid = m.get("pid", "—")
    tcin_id = m.get("tcin_id", "—")
    mapping_id = str(m.get("id", ""))

    hdr_col, conf_col = st.columns([4, 1])
    with hdr_col:
        st.subheader(f"⛔ No Match Found  ·  PID: {pid}  /  TCIN: {tcin_id}")
        st.caption("Confidence is below the 75% threshold — the engine could not reliably assign an impression.")
    with conf_col:
        st.metric(
            "Confidence",
            f"{score:.0%}",
            delta=f"{tier} tier",
            delta_color="off",
            help=f"Raw: {score:.4f}  ·  Threshold: 75%",
        )

    left, right = st.columns(2)

    with left:
        st.markdown("#### TCIN (Guest-Facing)")
        st.markdown(f"- **Color family:** `{m.get('tcin_color', '—')}`")
        st.markdown(f"- **Color name:** `{m.get('tcin_color_name', '—')}`")
        st.markdown(f"- **Size:** `{m.get('tcin_size', '—')}`")
        st.markdown(f"- **Departments:** `{', '.join(m.get('department_ids', []))}`")

        rnd = (m.get("match_round") or "").upper()
        if rnd:
            rnd_icon = _ROUND_ICON.get(rnd, "❓")
            rnd_desc = _ROUND_DESC.get(rnd, rnd)
            st.markdown(f"- **Match round:** {rnd_icon} `{rnd}` — _{rnd_desc}_")
        if m.get("color_match_reason"):
            st.markdown(f"- **Engine reason:** _{m['color_match_reason']}_")

        st.markdown("**Confidence**")
        st.markdown(_confidence_bar(score, tier), unsafe_allow_html=True)

    with right:
        st.markdown("#### Assign Impression")
        options, sorted_cands = _get_candidate_options(m, pid)

        if sorted_cands:
            st.caption("Engine top candidates (ranked by score):")
            for c in sorted_cands[:5]:
                c_score = c.get("score", 0)
                icon = "🟢" if c_score >= 0.85 else "🔵" if c_score >= 0.75 else "🟡"
                st.caption(f"  {icon} **{c.get('impression_name')}**  —  {c_score:.2f}  ·  {c.get('reason', '')}")
        else:
            st.caption("No engine candidates. Showing all impressions for this PID.")

        if not options:
            st.warning("No impression options found for this PID.")
        else:
            selected = st.selectbox(
                "Choose impression to assign:",
                options=options,
                key=f"nm_select_{mapping_id}",
            )

            notes = st.text_area(
                "Notes (optional)",
                placeholder="Why is this the right impression?",
                height=80,
                key=f"nm_notes_{mapping_id}",
            )

            col_assign, col_skip = st.columns([2, 1])
            with col_assign:
                if st.button(
                    "✓ Assign Impression",
                    type="primary",
                    key=f"nm_assign_{mapping_id}",
                    use_container_width=True,
                ):
                    success = _submit_feedback(m, FeedbackAction.CORRECT, reviewer, selected, notes)
                    if success:
                        reviewed.add(mapping_id)
                        st.session_state["reviewed_ids"] = reviewed
                        st.toast(f"Assigned: {selected}", icon="✅")
            with col_skip:
                if st.button("Skip", key=f"nm_skip_{mapping_id}", use_container_width=True):
                    reviewed.add(mapping_id)
                    st.session_state["reviewed_ids"] = reviewed
                    st.toast("Skipped", icon="⏭️")


# ─── Standard review card ──────────────────────────────────────────────────────


def _render_review_card(m: dict, reviewer: str, reviewed: set):
    tier = m.get("confidence_tier", "LOW")
    score = m.get("color_confidence", 0.0)
    pid = m.get("pid", "—")
    tcin_id = m.get("tcin_id", "—")
    impression = m.get("matched_impression_name") or "_(no match found)_"
    mapping_id = str(m.get("id", ""))

    icon = _TIER_ICON.get(tier, "⚪")
    hdr_col, conf_col = st.columns([4, 1])
    with hdr_col:
        st.subheader(f"{icon} PID: {pid}  /  TCIN: {tcin_id}")
    with conf_col:
        st.metric("Confidence", f"{score:.0%}", delta=f"{tier} tier", delta_color="off", help=f"Raw: {score:.4f}")

    left, right = st.columns(2)

    with left:
        st.markdown("#### TCIN (Guest-Facing)")
        st.markdown(f"- **Color family:** `{m.get('tcin_color', '—')}`")
        st.markdown(f"- **Color name:** `{m.get('tcin_color_name', '—')}`")
        st.markdown(f"- **Size:** `{m.get('tcin_size', '—')}`")
        st.markdown(f"- **Departments:** `{', '.join(m.get('department_ids', []))}`")

    with right:
        st.markdown("#### Matched Impression (Design)")
        st.markdown(f"- **Impression:** `{m.get('matched_impression_name', '—')}`")
        st.markdown(f"- **Size:** `{m.get('variation_size', '—')}`")
        rnd = (m.get("match_round") or "").upper()
        if rnd:
            rnd_icon = _ROUND_ICON.get(rnd, "❓")
            rnd_desc = _ROUND_DESC.get(rnd, rnd)
            st.markdown(f"- **Match round:** {rnd_icon} `{rnd}` — _{rnd_desc}_")
        if m.get("llm_rationale"):
            st.markdown(f"- **LLM note:** _{m['llm_rationale']}_")
        if m.get("color_match_reason"):
            st.markdown(f"- **Match reason:** _{m['color_match_reason']}_")

    st.markdown(_confidence_bar(score, tier), unsafe_allow_html=True)

    # Possible impressions — always shown when candidates exist
    candidates = m.get("color_possible_values", [])
    sorted_cands = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True) if candidates else []
    if sorted_cands:
        st.markdown("**Possible impressions (engine candidates):**")
        for c in sorted_cands[:5]:
            c_score = c.get("score", 0)
            c_tier = "HIGH" if c_score >= 0.85 else "GOOD" if c_score >= 0.75 else "FAIR" if c_score >= 0.50 else "LOW"
            c_icon = _TIER_ICON.get(c_tier, "⚪")
            st.markdown(f"  {c_icon} **{c.get('impression_name', '?')}** — {c_score:.0%}  ·  {c.get('reason', '')}")

    st.markdown("---")

    st.markdown("#### Your Decision")
    action_col, suggest_col, note_col = st.columns([1, 2, 2])

    with action_col:
        action_label = st.radio(
            "Action",
            ["Confirm", "Reject", "Correct"],
            key=f"action_{mapping_id}",
        )

    action_map = {
        "Confirm": FeedbackAction.CONFIRM,
        "Reject": FeedbackAction.REJECT,
        "Correct": FeedbackAction.CORRECT,
    }
    action = action_map[action_label]

    with suggest_col:
        impression_options = _get_impression_options(pid)
        suggested_impression: str | None = None
        if impression_options:
            cand_names = [c.get("impression_name", "") for c in sorted_cands if c.get("impression_name")]
            other_options = [i for i in impression_options if i not in cand_names]
            ordered_options = cand_names + other_options

            default_idx = 0
            if impression in ordered_options:
                default_idx = ordered_options.index(impression)

            selected_in_dropdown = st.selectbox(
                "Impression (current or correction):",
                options=ordered_options,
                index=default_idx,
                key=f"suggest_{mapping_id}",
                help="Candidates from the engine are listed first. Change this when selecting 'Correct'.",
            )
            if action == FeedbackAction.CORRECT:
                suggested_impression = selected_in_dropdown
        else:
            if action == FeedbackAction.CORRECT:
                suggested_impression = st.text_input(
                    "Type correct impression name",
                    placeholder="e.g. TUSCAN BROWN",
                    key=f"suggest_text_{mapping_id}",
                )

    with note_col:
        notes = st.text_area(
            "Notes (optional)",
            placeholder="Why are you making this decision?",
            height=100,
            key=f"notes_{mapping_id}",
        )

    # Outcome banner — tells the reviewer what signal they're sending to the engine
    _render_outcome_banner(action_label, m.get("matched_impression_name"), suggested_impression)

    can_submit = True
    if action == FeedbackAction.CORRECT and not suggested_impression:
        st.warning("Please select or type the correct impression before submitting.")
        can_submit = False

    submit_label = {
        "Confirm": "✓ Confirm",
        "Reject": "✗ Reject",
        "Correct": "✏ Submit Correction",
    }

    if st.button(
        submit_label[action_label],
        type="primary",
        disabled=not can_submit,
        key=f"submit_{mapping_id}",
    ):
        success = _submit_feedback(m, action, reviewer, suggested_impression, notes)
        if success:
            reviewed.add(mapping_id)
            st.session_state["reviewed_ids"] = reviewed
            st.toast(f"{action_label} saved — moving to next item.", icon="✅")
