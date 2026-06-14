"""Search by Department — expandable PID rows with glimpse and inline review."""

from __future__ import annotations

import httpx
import streamlit as st
from plm_tcin_mapper_client import api_client
from plm_tcin_mapper_client.utils import needs_review_icon

# ─── Cached data loaders ───────────────────────────────────────────────────────


@st.cache_data(ttl=300, show_spinner=False)
def _load_dept_ids() -> list[str]:
    """Fetch all distinct departments from the API."""
    try:
        result = api_client.get_departments()
        return sorted(result)
    except httpx.HTTPError:
        return []


@st.cache_data(ttl=60, show_spinner=False)
def _load_pids_for_dept(
    dept_id: str, pid_filter: str, status_filter: str | None = None, limit: int = 500
) -> list[dict]:
    """Return per-PID aggregated rows for the department via API.

    Sorted worst-confidence-first so needs-review PIDs appear at the top.
    Status filter: None (all), "needs_review", "confirmed", "rejected", "corrected".
    """
    try:
        pids = api_client.get_pids_for_department(dept_id)

        # Apply additional filters
        if pid_filter:
            pids = [p for p in pids if pid_filter in p.get("pid", "")]

        if status_filter == "needs_review":
            pids = [p for p in pids if p.get("needs_review", False)]
        elif status_filter == "confirmed":
            pids = [p for p in pids if p.get("confirmed", 0) > 0]
        elif status_filter == "rejected":
            pids = [p for p in pids if p.get("rejected", 0) > 0]
        elif status_filter == "corrected":
            pids = [p for p in pids if p.get("corrected", 0) > 0]

        # Already sorted by confidence asc (worst first) from API
        return pids[:limit]
    except httpx.HTTPError:
        return []


def _batch_load_mappings(dept_id: str, pids: list[str]) -> dict[str, list[dict]]:
    """Load all mapping docs for a list of PIDs via API. Returns {pid: [mapping_doc, ...]}."""
    by_pid: dict[str, list[dict]] = {}
    try:
        for pid in pids:
            result = api_client.get_mappings(pid=pid)
            mappings = result.get("items", [])
            if mappings:
                by_pid[pid] = mappings
    except httpx.HTTPError:
        pass
    return by_pid


def _batch_load_vars(pids: list[str]) -> dict[str, list[dict]]:
    """Load variation_records for a list of PIDs via API. Returns {pid: [var_doc, ...]}."""
    by_pid: dict[str, list[dict]] = {}
    try:
        for pid in pids:
            variations = api_client.get_variations(pid)
            if variations:
                var_docs = [{"impression_name": v} for v in variations]
                by_pid[pid] = var_docs
    except httpx.HTTPError:
        pass
    return by_pid


# ─── Page ─────────────────────────────────────────────────────────────────────


def render() -> None:
    from plm_tcin_mapper_client.pages.pid_lookup import render_pid_card

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

    # ── Run Matching for this department ──────────────────────────────────────
    with st.expander("⚙️ Run Matching Pipeline for this Department", expanded=False):
        rc1, rc2, rc3 = st.columns([2, 1, 1])
        with rc1:
            unmatched_only = st.checkbox(
                "Unmatched / NO_MATCH only",
                value=False,
                key=f"run_unmatched_{dept_id}",
                help=(
                    "OFF — re-run on ALL PIDs in this department (refreshes existing mappings).\n\n"
                    "ON — only process PIDs with no mapping yet or an explicit NO_MATCH."
                ),
            )
        with rc2:
            use_llm = st.checkbox("Use LLM", value=True, key=f"run_llm_{dept_id}")
        with rc3:
            run_dry = st.checkbox("Dry run", value=False, key=f"run_dry_{dept_id}")

        if st.button(
            f"▶ Run Matching — Dept {dept_id}",
            key=f"run_match_{dept_id}",
            type="primary",
            use_container_width=False,
        ):
            with st.spinner(f"Running matching pipeline for department {dept_id}…"):
                try:
                    resp = api_client.run_mappings(
                        {
                            "department": dept_id,
                            "unmatched_only": unmatched_only,
                            "use_llm": use_llm,
                            "dry_run": run_dry,
                        }
                    )
                    if run_dry:
                        st.info("🔍 Dry run — no changes saved.")
                        st.json(resp)
                    else:
                        st.success(
                            f"✅ Done — {resp.get('pids_matched', 0)} PIDs matched, "
                            f"{resp.get('total_mappings_written', 0)} mappings written."
                        )
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Total PIDs", resp.get("total_pids", 0))
                        m2.metric("Matched", resp.get("pids_matched", 0))
                        m3.metric("No Data", resp.get("pids_no_data", 0))
                        m4.metric("Errors", resp.get("pids_errored", 0))
                        # Bust the PID cache so the list refreshes
                        _load_pids_for_dept.clear()
                except httpx.HTTPError as e:
                    st.error(f"Matching failed: {e}")

    st.divider()

    with st.spinner("Loading PIDs…"):
        rows = _load_pids_for_dept(dept_id, pid_filter, status_filter_val, limit=50)

    if not rows:
        st.warning(f"No PIDs found in department **{dept_id}** matching your filters.")
        return

    st.caption(f"Showing {len(rows)} of {len(rows)} PIDs — worst confidence first.")

    # Batch-load all mappings and variations
    pids_to_load = [r["pid"] for r in rows]
    all_mappings = _batch_load_mappings(dept_id, pids_to_load)
    all_vars = _batch_load_vars(pids_to_load)

    # ── Expandable PID rows ────────────────────────────────────────────────────
    for row in rows:
        pid = row["pid"]
        mapping_docs = all_mappings.get(pid, [])
        var_docs = all_vars.get(pid, [])

        # Compute icons and metrics
        needs_review = row.get("needs_review", False)
        avg_conf = row.get("avg_confidence", 0.0)
        icon = needs_review_icon(needs_review, avg_conf)
        pct = int(avg_conf * 100)
        n_tcins = row.get("total", 0)

        with st.expander(
            f"{icon} **{pid}**  ·  {n_tcins} TCINs  ·  {pct}% avg confidence",
            expanded=False,
        ):
            if not mapping_docs:
                st.caption("No mappings yet — run the matching pipeline above.")
            else:
                render_pid_card(pid, mapping_docs, var_docs, key_suffix=f"dept_{dept_id}_{pid}")
