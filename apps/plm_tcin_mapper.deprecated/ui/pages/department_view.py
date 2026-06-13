"""Search by Department — expandable PID rows with glimpse and inline review."""

from __future__ import annotations

import streamlit as st

from plm_tcin_mapper.ui.db import get_db
from plm_tcin_mapper.ui.utils import needs_review_icon

# ─── Cached data loaders ───────────────────────────────────────────────────────


@st.cache_data(ttl=300, show_spinner=False)
def _load_dept_ids() -> list[str]:
    db = get_db()
    if db is None:
        return []
    try:
        ids = db.tcin_records.distinct("department_ids")
        return sorted(str(i) for i in ids if i)
    except Exception:
        return []


@st.cache_data(ttl=60, show_spinner=False)
def _load_pids_for_dept(
    dept_id: str, pid_filter: str, status_filter: str | None = None, limit: int = 50
) -> list[dict]:
    """Return per-PID aggregated rows for the department.

    Sorted worst-confidence-first so needs-review PIDs appear at the top.
    Status filter: None (all), "needs_review", "confirmed", "rejected", "corrected".
    """
    db = get_db()
    if db is None:
        return []
    try:
        match: dict = {"department_ids": dept_id}
        if pid_filter:
            match["pid"] = pid_filter

        if status_filter == "needs_review":
            match["status"] = {"$in": ["NO_MATCH", "NEEDS_REVIEW", "NEEDS_SPOT_CHECK"]}
        elif status_filter == "confirmed":
            match["status"] = "CONFIRMED"
        elif status_filter == "rejected":
            match["status"] = "REJECTED"
        elif status_filter == "corrected":
            match["status"] = "CORRECTED"

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$pid",
                    "total": {"$sum": 1},
                    "avg_confidence": {"$avg": "$color_confidence"},
                    "statuses": {"$addToSet": "$status"},
                }
            },
            {"$sort": {"avg_confidence": 1}},
            {"$limit": limit},
        ]
        rows = []
        for d in db.mappings.aggregate(pipeline):
            statuses = d.get("statuses", [])
            needs_review = any(s in ("NO_MATCH", "NEEDS_REVIEW", "NEEDS_SPOT_CHECK") for s in statuses)
            rows.append(
                {
                    "pid": d["_id"],
                    "total": d["total"],
                    "avg_confidence": round(d.get("avg_confidence") or 0.0, 3),
                    "needs_review": needs_review,
                }
            )
        return rows
    except Exception:
        return []


@st.cache_data(ttl=60, show_spinner=False)
def _batch_load_mappings(dept_id: str, pids: tuple[str, ...]) -> dict[str, list[dict]]:
    """Load all mapping docs for a list of PIDs in one query. Returns {pid: [mapping_doc, ...]}."""
    db = get_db()
    if db is None:
        return {}
    try:
        docs = list(db.mappings.find({"pid": {"$in": list(pids)}}).sort([("pid", 1), ("tcin_id", 1)]))
        by_pid: dict[str, list[dict]] = {}
        for d in docs:
            by_pid.setdefault(d["pid"], []).append(d)
        return by_pid
    except Exception:
        return {}


@st.cache_data(ttl=60, show_spinner=False)
def _batch_load_vars(pids: tuple[str, ...]) -> dict[str, list[dict]]:
    """Load variation_records for a list of PIDs in one query. Returns {pid: [var_doc, ...]}."""
    db = get_db()
    if db is None:
        return {}
    try:
        docs = list(db.variation_records.find({"pid": {"$in": list(pids)}}))
        by_pid: dict[str, list[dict]] = {}
        for d in docs:
            by_pid.setdefault(d["pid"], []).append(d)
        return by_pid
    except Exception:
        return {}


# ─── Page ─────────────────────────────────────────────────────────────────────


def render() -> None:
    from plm_tcin_mapper.ui.pages.pid_lookup import render_pid_card

    st.header("Search by Department")
    st.caption("Browse all products in a department. Expand a row to see detail and submit overrides.")

    # ── Filters ───────────────────────────────────────────────────────────────
    dept_ids = _load_dept_ids()
    f1, f2, f3 = st.columns([2, 2, 2])
    with f1:
        if dept_ids:
            dept_id = st.selectbox("Department", options=dept_ids)
        else:
            dept_id = st.text_input("Department ID", placeholder="e.g. 214")
    with f2:
        raw_pid_filter = st.text_input("Filter by PID", placeholder="optional — e.g. PID-009E83")
    with f3:
        status_filter = st.selectbox(
            "Status",
            options=["All", "Needs Review", "Confirmed", "Rejected", "Corrected"],
            help="Filter by mapping review status",
        )

    pid_filter = raw_pid_filter.strip().upper()
    status_map = {
        "All": None,
        "Needs Review": "needs_review",
        "Confirmed": "confirmed",
        "Rejected": "rejected",
        "Corrected": "corrected",
    }
    status_filter_val = status_map[status_filter]

    if not dept_id:
        st.info("Select a department above.")
        return

    # ── Load PID list ─────────────────────────────────────────────────────────
    with st.spinner(f"Loading department {dept_id} …"):
        pid_rows = _load_pids_for_dept(dept_id, pid_filter, status_filter=status_filter_val, limit=50)

    if not pid_rows:
        msg = f"No products found for department **{dept_id}**"
        msg += f" matching PID `{pid_filter}`." if pid_filter else "."
        st.warning(msg)
        return

    st.divider()

    # ── Summary strip ─────────────────────────────────────────────────────────
    needs_review_count = sum(1 for r in pid_rows if r["needs_review"])
    overridden_count = sum(1 for r in pid_rows if bool(st.session_state.get("pid_overrides", {}).get(r["pid"])))
    m1, m2, m3 = st.columns(3)
    m1.metric("Products shown", len(pid_rows), help="Capped at 50, sorted worst confidence first")
    m2.metric("Needs Review", needs_review_count)
    m3.metric("Overridden this session", overridden_count)

    st.markdown("")

    # ── Batch load data for all PIDs ──────────────────────────────────────────
    all_pids = tuple(r["pid"] for r in pid_rows)
    with st.spinner("Loading mapping details …"):
        mappings_by_pid = _batch_load_mappings(dept_id, all_pids)
        vars_by_pid = _batch_load_vars(all_pids)

    expand_default: bool = st.session_state.get("expand_default", True)

    # ── PID rows ──────────────────────────────────────────────────────────────
    for row in pid_rows:
        pid = row["pid"]
        avg_conf = row["avg_confidence"]
        icon = needs_review_icon(row["needs_review"], avg_conf)
        pct = int(avg_conf * 100)

        overridden = bool(st.session_state.get("pid_overrides", {}).get(pid))
        override_tag = " · 🔄 Overridden" if overridden else ""
        review_tag = " · Needs Review" if row["needs_review"] and not overridden else ""

        header = f"{icon} {pid} — {pct}% match{review_tag}{override_tag}"

        mapping_docs = mappings_by_pid.get(pid, [])
        var_docs = vars_by_pid.get(pid, [])

        # Glimpse: top 3 highest-confidence color→impression pairs
        top3 = sorted(mapping_docs, key=lambda m: m.get("color_confidence", 0), reverse=True)[:3]
        glimpse_parts = []
        for m in top3:
            color = (m.get("tcin_color_name") or m.get("tcin_color") or "").title()
            impression = m.get("matched_impression_name") or "no match"
            glimpse_parts.append(f"{color} → {impression}")
        if len(mapping_docs) > 3:
            glimpse_parts.append(f"+{len(mapping_docs) - 3} more")
        glimpse = "  ·  ".join(glimpse_parts)

        with st.expander(header, expanded=expand_default):
            if glimpse:
                st.caption(glimpse)
                st.markdown("")

            if mapping_docs:
                render_pid_card(pid, mapping_docs, var_docs, key_suffix=f"dept_{pid}", review_enabled=True)
            else:
                st.info("No mapping data loaded for this PID.")
