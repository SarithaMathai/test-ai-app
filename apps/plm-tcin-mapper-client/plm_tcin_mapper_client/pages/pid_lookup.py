"""Search by PID — colour-grouped mappings with whole-PID review form."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

import httpx
import streamlit as st

from plm_tcin_mapper_client import api_client
from plm_tcin_mapper_client.enums import FeedbackAction
from plm_tcin_mapper_client.utils import confidence_badge, size_sort_key

_NULL_SENTINEL = "___NULL___"  # sentinel for "clear impression / set to null"


# ─── API helpers ────────────────────────────────────────────────────────────────


def _impression_options(pid: str) -> list[str]:
    """Fetch distinct impression variations for a PID."""
    try:
        variations = api_client.get_variations(pid)
        return sorted(set(variations))
    except httpx.HTTPError as e:
        st.error(f"Failed to load impression options: {e}")
        return []


def _save_correction(m: dict, impression_name: str) -> bool:
    """Save a correction by submitting feedback to the API."""
    try:
        mapping_id = str(m.get("id", ""))
        pid = m.get("pid", "")

        feedback = {
            "mapping_id": mapping_id,
            "pid": pid,
            "tcin_id": m.get("tcin_id", ""),
            "action": FeedbackAction.CORRECT.value,
            "tcin_color": m.get("tcin_color"),
            "tcin_color_name": m.get("tcin_color_name"),
            "tcin_size": m.get("tcin_size"),
            "department_ids": m.get("department_ids", []),
            "match_round": m.get("match_round"),
            "original_confidence_tier": m.get("confidence_tier"),
            "suggested_impression_name": impression_name,
            "original_impression_name": m.get("matched_impression_name"),
            "original_color_confidence": m.get("color_confidence"),
        }

        api_client.submit_feedback(feedback)
        return True
    except httpx.HTTPError as e:
        st.error(f"Error saving correction: {e}")
        return False


def _clear_impression(m: dict) -> bool:
    """Clear a mapping (set status to NO_MATCH) via API."""
    try:
        mapping_id = str(m.get("id", ""))
        api_client.clear_mapping(mapping_id)
        return True
    except httpx.HTTPError as e:
        st.error(f"Error clearing impression: {e}")
        return False


# ─── PID-level review callbacks ────────────────────────────────────────────────


def _open_pid_review_cb(pid: str, mapping_docs: list[dict], key_suffix: str) -> None:
    """Open review mode and snapshot original impressions for change detection."""
    st.session_state[f"_pid_rev_{pid}_{key_suffix}"] = True
    originals: dict[tuple, str] = {}
    for m in mapping_docs:
        color_key = (m.get("tcin_color") or "", m.get("tcin_color_name") or "")
        if color_key not in originals:
            originals[color_key] = m.get("matched_impression_name") or ""
    st.session_state[f"_pid_orig_{pid}_{key_suffix}"] = originals


def _cancel_pid_review_cb(pid: str, key_suffix: str) -> None:
    st.session_state[f"_pid_rev_{pid}_{key_suffix}"] = False


def _save_pid_review_cb(pid: str, mapping_docs: list[dict], key_suffix: str) -> None:
    """Save all changed rows from the whole-PID review form and reload from API."""
    originals: dict = st.session_state.get(f"_pid_orig_{pid}_{key_suffix}", {})

    color_groups: dict[tuple, list[dict]] = defaultdict(list)
    for m in mapping_docs:
        key = (m.get("tcin_color") or "", m.get("tcin_color_name") or "")
        color_groups[key].append(m)

    saved = cleared = 0
    for color_key, color_maps in color_groups.items():
        tcin_color, tcin_color_name = color_key
        sel_key = f"_sel_{pid}_{tcin_color}_{tcin_color_name}_{key_suffix}"
        chosen = st.session_state.get(sel_key)
        original = originals.get(color_key, "")

        if chosen is None or chosen == "":
            continue  # blank placeholder — no action

        if chosen == _NULL_SENTINEL:
            if original:  # only clear if there was something to clear
                for m in color_maps:
                    if _clear_impression(m):
                        cleared += 1
        elif chosen != original:
            for m in color_maps:
                if chosen != (m.get("matched_impression_name") or "") and _save_correction(m, chosen):
                    saved += 1

    st.session_state[f"_pid_rev_{pid}_{key_suffix}"] = False
    ts = datetime.now().strftime("%H:%M:%S")
    parts = []
    if saved:
        parts.append(f"{saved} updated")
    if cleared:
        parts.append(f"{cleared} cleared")
    label = (", ".join(parts) + f" · {ts}") if parts else f"No changes · {ts}"
    st.session_state[f"_toast_{pid}"] = (label, bool(saved or cleared))

    # Reload mappings from API to show fresh data
    if saved or cleared:
        st.session_state[f"_reload_{pid}"] = True
        st.rerun()


# ─── Display helpers ───────────────────────────────────────────────────────────


def _options_for(m: dict, impression_options: list[str]) -> list[str]:
    raw = m.get("color_possible_values", [])
    top = [
        c["impression_name"]
        for c in sorted(raw, key=lambda x: x.get("score", 0), reverse=True)
        if c.get("impression_name")
    ]
    rest = [i for i in impression_options if i not in top]
    return top + rest or impression_options


def _method_label(m: dict) -> str:
    """Sub-line under the impression showing how the match was made."""
    status = m.get("status", "")
    if status == "CORRECTED":
        return '👤 <span style="color:#2563eb;font-size:0.76em;font-weight:600">Human entered</span>'
    if m.get("llm_rationale"):
        rationale = m["llm_rationale"][:55] + ("…" if len(m["llm_rationale"]) > 55 else "")
        return f'🤖 <span style="color:#888;font-size:0.76em">LLM — {rationale}</span>'
    reason = m.get("color_match_reason") or ""
    if reason:
        return f'⚙️ <span style="color:#888;font-size:0.76em">{reason[:55]}</span>'
    return ""


_CANDIDATE_GAP = 0.20


def _competing_candidates_html(m: dict) -> str:
    candidates = sorted(
        m.get("color_possible_values", []),
        key=lambda x: x.get("score", 0),
        reverse=True,
    )
    if len(candidates) < 2:
        return ""
    top_score = candidates[0].get("score", 0)
    competing = [c for c in candidates if top_score - c.get("score", 0) <= _CANDIDATE_GAP and c.get("impression_name")]
    if len(competing) < 2:
        return ""
    badges = []
    for c in competing:
        name = c["impression_name"]
        pct = round(c.get("score", 0) * 100)
        score = c.get("score", 0)
        bg, fg = (
            ("#d1f0d1", "#1a5c1a")
            if score >= 0.85
            else (("#fff3cd", "#7d5a00") if score >= 0.60 else ("#fde8e8", "#8b1a1a"))
        )
        badges.append(
            f'<span style="background:{bg};color:{fg};padding:1px 7px;border-radius:10px;'
            f'font-size:0.73em;font-weight:600;display:inline-block;margin:0 3px 0 0">'
            f"{name} {pct}%</span>"
        )
    return '<span style="color:#aaa;font-size:0.73em;margin-right:4px">⚖️ debating:</span>' + "".join(badges)


# ─── Colour row ────────────────────────────────────────────────────────────────


def _render_color_row(
    pid: str,
    color_key: tuple[str, str],
    color_maps: list[dict],
    impression_options: list[str],
    key_suffix: str,
    review_open: bool,
    originals: dict,
    col_w: list[float],
) -> None:
    tcin_color, tcin_color_name = color_key
    color_label = f"{tcin_color} / {tcin_color_name}".strip(" /") or "—"

    m0 = color_maps[0]
    is_no_match = not m0.get("matched_impression_name")
    is_human = m0.get("status") == "CORRECTED"
    impression = m0.get("matched_impression_name") or "_(no match)_"
    confidence = max((m.get("color_confidence") or 0.0) for m in color_maps)

    sel_key = f"_sel_{pid}_{tcin_color}_{tcin_color_name}_{key_suffix}"

    # Detect if reviewer has changed this row from its original
    is_changed = False
    if review_open:
        original = originals.get(color_key, "")
        current_sel = st.session_state.get(sel_key)
        if current_sel is None or current_sel == "":
            is_changed = False
        elif current_sel == _NULL_SENTINEL:
            is_changed = bool(original)
        else:
            is_changed = current_sel != original

    # ── Row background by confidence tier ────────────────────────────────────
    if is_no_match:
        row_bg = "#fde8e8"  # stronger red
        border_color = "#f87171"
    elif confidence >= 0.85:
        row_bg = "#dcfce7"  # stronger green
        border_color = "#4ade80"
    else:
        row_bg = "#fef08a"  # stronger yellow
        border_color = "#facc15"

    # ── Sizes subsection (built first, shared between both render paths) ──────
    sorted_maps = sorted(color_maps, key=lambda m: size_sort_key(m.get("tcin_size") or ""))
    size_parts = []
    for m in sorted_maps:
        ts = m.get("tcin_size") or ""
        vs = m.get("variation_size") or ""
        if not ts:
            continue
        # Show mismatch arrow only when guest-facing size label differs from design label
        if vs and ts.lower().replace(" ", "") != vs.lower().replace(" ", ""):
            size_parts.append(f'<b style="color:#b45309">{ts} → {vs}</b>')
        else:
            size_parts.append(ts)

    sizes_html = (
        f'<div style="padding:4px 0 10px 1.2rem;color:#888;font-size:0.76em">'
        f'<span style="color:#bbb">Sizes: </span>{"  ·  ".join(size_parts)}</div>'
        if size_parts
        else ""
    )

    if review_open:
        # ── Review mode: Streamlit columns (widgets needed), left-border indicator ──
        st.markdown(
            f'<div style="border-left:4px solid {border_color};'
            f'padding-left:6px;margin:2px 0 0 0;border-radius:0 4px 4px 0"></div>',
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns(col_w)

        if is_changed:
            c1.markdown(
                f'<span style="color:#2563eb;font-weight:600">✏️ {color_label}</span>',
                unsafe_allow_html=True,
            )
        else:
            c1.write(color_label)

        c3.markdown(
            confidence_badge(confidence) if not is_no_match else '<span style="color:#ccc;font-size:0.82em">—</span>',
            unsafe_allow_html=True,
        )

        opts = _options_for(m0, impression_options)

        def _fmt(x: str) -> str:
            if x == _NULL_SENTINEL:
                return "— Clear / set null —"
            if x == "":
                return "— select impression —"
            return x

        if is_no_match:
            select_opts = ["", _NULL_SENTINEL, *opts]
            default_idx = 0
        else:
            select_opts = [_NULL_SENTINEL, *opts]
            idx = opts.index(impression) if impression in opts else 0
            default_idx = idx + 1

        c2.selectbox(
            "impression",
            select_opts,
            index=default_idx,
            format_func=_fmt,
            key=sel_key,
            label_visibility="collapsed",
        )

        if sizes_html:
            st.markdown(sizes_html, unsafe_allow_html=True)

    else:
        # ── Display mode: pure HTML row — full background color ────────────────
        method = _method_label(m0)
        candidates = _competing_candidates_html(m0)
        sub = []
        if method:
            sub.append(f"<small>{method}</small>")
        if candidates:
            sub.append(f"<small>{candidates}</small>")
        impression_cell = impression + ("".join(f"<br>{s}" for s in sub) if sub else "")

        conf_cell = (
            '<span style="color:#aaa;font-size:0.82em">—</span>'
            if is_human
            else (
                confidence_badge(confidence)
                if not is_no_match
                else '<span style="color:#ccc;font-size:0.82em">—</span>'
            )
        )

        st.markdown(
            f'<div style="background:{row_bg};border-radius:6px;'
            f'padding:7px 12px 4px 12px;margin-bottom:2px">'
            f'<div style="display:flex;gap:8px;align-items:flex-start">'
            f'  <div style="flex:2.2;min-width:0;font-size:0.92em">{color_label}</div>'
            f'  <div style="flex:3.2;min-width:0;font-size:0.92em;line-height:1.5">{impression_cell}</div>'
            f'  <div style="flex:1.2;min-width:0">{conf_cell}</div>'
            f"</div>"
            + (
                f'<div style="font-size:0.75em;color:#aaa;padding:2px 0 4px 0">'
                f'<span style="color:#ccc">Sizes: </span>{"  ·  ".join(size_parts)}</div>'
                if size_parts
                else ""
            )
            + "</div>",
            unsafe_allow_html=True,
        )


# ─── PID card (shared with department_view) ───────────────────────────────────


def render_pid_card(
    pid: str,
    mapping_docs: list[dict],
    var_docs: list[dict],
    key_suffix: str = "",
    review_enabled: bool = True,
) -> None:
    st.session_state.setdefault("pid_overrides", {}).setdefault(pid, {})

    review_open = review_enabled and st.session_state.get(f"_pid_rev_{pid}_{key_suffix}", False)
    originals: dict = st.session_state.get(f"_pid_orig_{pid}_{key_suffix}", {})

    # ── Header ─────────────────────────────────────────────────────────────────
    confs = [m.get("color_confidence", 0.0) for m in mapping_docs if m.get("color_confidence") is not None]
    avg_conf = sum(confs) / len(confs) if confs else 0.0
    needs_review = any(m.get("status") in ("NO_MATCH", "NEEDS_REVIEW", "NEEDS_SPOT_CHECK") for m in mapping_docs)

    h1, h2, h3 = st.columns([3.5, 1.2, 1.5])
    with h1:
        dept_ids: set[str] = set()
        for m in mapping_docs:
            dept_ids.update(m.get("department_ids", []))
        st.markdown(f"**Id:** {pid}")
        st.caption(f"Dept: {', '.join(sorted(dept_ids)) or '—'}  ·  {len(mapping_docs)} TCINs")
    with h2:
        st.metric("Avg Match", f"{int(avg_conf * 100)}%")
    with h3:
        if needs_review:
            st.error("Needs Review", icon="⚠️")
        else:
            st.success("Good", icon="✅")

    # Review button on its own line, right-aligned
    if review_enabled:
        _, rev_col = st.columns([5, 2])
        with rev_col:
            if review_open:
                st.button(
                    "Cancel",
                    key=f"_cancel_rev_{pid}_{key_suffix}",
                    use_container_width=True,
                    on_click=_cancel_pid_review_cb,
                    args=(pid, key_suffix),
                )
            else:
                st.button(
                    "✏️ Review PID",
                    key=f"_open_rev_{pid}_{key_suffix}",
                    use_container_width=True,
                    on_click=_open_pid_review_cb,
                    args=(pid, mapping_docs, key_suffix),
                )

    # Toast from previous save
    toast_data = st.session_state.pop(f"_toast_{pid}", None)
    if toast_data:
        msg, ok = toast_data
        st.toast(msg, icon="✅" if ok else "ℹ️")

    st.markdown("")

    # ── Impression options ─────────────────────────────────────────────────────
    impression_options = sorted({v.get("impression_name", "") for v in var_docs if v.get("impression_name")})
    if not impression_options:
        impression_options = _impression_options(pid)

    # ── Group by colour ────────────────────────────────────────────────────────
    color_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for m in mapping_docs:
        key = (m.get("tcin_color") or "", m.get("tcin_color_name") or "")
        color_groups[key].append(m)

    def _sort_groups(item: tuple) -> tuple:
        k, v = item
        has_no_match = any(m.get("status") == "NO_MATCH" for m in v)
        return (0 if has_no_match else 1, k[0].lower())

    # ── Column headers ─────────────────────────────────────────────────────────
    col_w = [2.2, 3.2, 1.2]
    h = st.columns(col_w)
    for col, lbl in zip(h, ["Color  (guest)", "Impression  (design)", "Confidence"], strict=False):
        col.markdown(f"<small><b>{lbl}</b></small>", unsafe_allow_html=True)
    st.markdown('<hr style="margin:4px 0 6px 0;border-color:#eee">', unsafe_allow_html=True)

    # ── Colour rows ────────────────────────────────────────────────────────────
    for color_key, color_maps in sorted(color_groups.items(), key=_sort_groups):
        _render_color_row(
            pid,
            color_key,
            color_maps,
            impression_options,
            key_suffix,
            review_open,
            originals,
            col_w,
        )

    # ── Save / Cancel footer (only when review is open) ────────────────────────
    if review_open:
        st.markdown("")
        f1, f2, _ = st.columns([2, 1, 3])
        f1.button(
            "💾 Save All Changes",
            key=f"_save_all_{pid}_{key_suffix}",
            type="primary",
            use_container_width=True,
            on_click=_save_pid_review_cb,
            args=(pid, mapping_docs, key_suffix),
        )
        f2.button(
            "Cancel",
            key=f"_cancel_footer_{pid}_{key_suffix}",
            use_container_width=True,
            on_click=_cancel_pid_review_cb,
            args=(pid, key_suffix),
        )


# ─── Page entry point ──────────────────────────────────────────────────────────


def render() -> None:
    st.header("Search by PID")
    st.caption("Enter a Product ID to view TCIN → Impression mappings.")

    col1, col2 = st.columns([4, 1])
    with col1:
        raw_pid = st.text_input(
            "Product ID (PID)",
            placeholder="e.g. PID-0L20P5",
            label_visibility="collapsed",
        )
    with col2:
        search = st.button("Search", type="primary", use_container_width=True)

    pid = raw_pid.strip().upper()

    if not pid:
        st.info("Enter a PID above and click Search.")
        return

    if not search and st.session_state.get("last_pid_searched") != pid and not raw_pid:
        return

    try:
        with st.spinner(f"Loading {pid} …"):
            result = api_client.get_mappings(pid=pid)
            mapping_docs = result.get("mappings", [])

            # Get variations for this PID
            variations = api_client.get_variations(pid)
            var_docs = [{"impression_name": v} for v in variations]
    except httpx.HTTPError as e:
        st.error(f"Failed to load mappings: {e}")
        return

    if not mapping_docs and not var_docs:
        st.warning(f"No records found for **{pid}**. Check the PID and try again.")
        return

    st.session_state["last_pid_searched"] = pid
    st.divider()
    render_pid_card(pid, mapping_docs, var_docs, key_suffix="pid_view")
