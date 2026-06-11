"""Admin — app-wide settings that persist for the current session."""

from __future__ import annotations

import streamlit as st

from plm_tcin_mapper.ui.db import get_db


def render() -> None:
    st.header("System Admin")
    st.caption("Configure app behavior. Changes apply immediately and persist for your session.")

    # ── Department view settings ───────────────────────────────────────────────
    st.markdown("### Department View")

    if "expand_default" not in st.session_state:
        st.session_state.expand_default = True

    new_val = st.toggle(
        "Expand all PID rows by default",
        value=st.session_state.expand_default,
        help="When on, every PID row loads expanded in the Department view. Turn off to start all rows collapsed.",
    )
    if new_val != st.session_state.expand_default:
        st.session_state.expand_default = new_val
        st.toast("Setting saved — navigate to Department view to see the change.", icon="✅")

    if st.session_state.expand_default:
        st.caption("Department view loads with all PIDs expanded.")
    else:
        st.caption("Department view loads with all PIDs collapsed — click a row to expand.")

    st.divider()

    # ── Confidence tiers (informational) ──────────────────────────────────────
    st.markdown("### Confidence Color Scale")
    st.caption("Thresholds used for the High / Good / Fair / Low badges throughout the app.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            '<div style="background:#d1f0d1;color:#1a5c1a;padding:8px 12px;border-radius:8px;text-align:center;font-weight:700;font-size:0.9em">HIGH<br><small>≥ 85%</small></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            '<div style="background:#c1ddf1;color:#1a4a7d;padding:8px 12px;border-radius:8px;text-align:center;font-weight:700;font-size:0.9em">GOOD<br><small>70–85%</small></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            '<div style="background:#fff3cd;color:#7d5a00;padding:8px 12px;border-radius:8px;text-align:center;font-weight:700;font-size:0.9em">FAIR<br><small>50–70%</small></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            '<div style="background:#fde8e8;color:#8b1a1a;padding:8px 12px;border-radius:8px;text-align:center;font-weight:700;font-size:0.9em">LOW<br><small>&lt; 50%</small></div>',
            unsafe_allow_html=True,
        )
    st.caption("These thresholds match the matching pipeline's AUTO_CONFIRM / LLM_ASSISTED / NEEDS_SPOT_CHECK / NEEDS_REVIEW tiers.")

    st.divider()

    # ── Data status ───────────────────────────────────────────────────────────
    st.markdown("### Data Source & MongoDB Status")
    db = get_db()
    if db is None:
        st.error("❌ MongoDB is not reachable. Make sure it is running and accessible.")
    else:
        try:
            counts = {
                "Mappings":          db.mappings.estimated_document_count(),
                "TCIN Records":      db.tcin_records.estimated_document_count(),
                "Variation Records": db.variation_records.estimated_document_count(),
                "Feedback":          db.feedback.estimated_document_count(),
            }
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Mappings", f"{counts['Mappings']:,}")
            with col2:
                st.metric("Total Feedback Records", f"{counts['Feedback']:,}")

            with st.expander("Full collection counts"):
                for name, count in counts.items():
                    st.markdown(f"- **{name}:** {count:,}")

            st.success("✅ MongoDB connected successfully.", icon="✓")
        except Exception as exc:
            st.warning(f"⚠️ Connected but could not fetch counts: {exc}")
