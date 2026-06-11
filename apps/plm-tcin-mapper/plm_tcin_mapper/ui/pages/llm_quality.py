"""LLM Quality — Streamlit page.

Shows cost, accuracy, latency, and hallucination rate for every LLM call
logged in the llm_calls collection.

Note: the FastAPI matching service does not yet write to llm_calls — this page
renders an empty-state until LLM call tracking is wired into the disambiguator.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from plm_tcin_mapper.ui.db import get_db

_LLM_CALLS_COL = "llm_calls"


# ─── Data loaders ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def _load_summary() -> dict[str, Any]:
    db = get_db()
    if db is None:
        return {}
    try:
        col = db[_LLM_CALLS_COL]
        pipeline = [
            {"$group": {
                "_id": None,
                "total_calls":       {"$sum": 1},
                "total_cost":        {"$sum": "$cost_usd"},
                "avg_latency_ms":    {"$avg": "$latency_ms"},
                "avg_confidence":    {"$avg": "$result_confidence"},
                "correct_count":     {"$sum": {"$cond": [{"$eq": ["$was_correct", True]}, 1, 0]}},
                "incorrect_count":   {"$sum": {"$cond": [{"$eq": ["$was_correct", False]}, 1, 0]}},
                "unreviewed_count":  {"$sum": {"$cond": [{"$eq": ["$was_correct", None]}, 1, 0]}},
                "hallucination_count": {"$sum": {"$cond": ["$is_hallucination", 1, 0]}},
            }}
        ]
        rows = list(col.aggregate(pipeline))
        return rows[0] if rows else {}
    except Exception as e:
        st.error(f"Error loading LLM summary: {e}")
        return {}


@st.cache_data(ttl=60)
def _load_by_model() -> list[dict]:
    db = get_db()
    if db is None:
        return []
    try:
        col = db[_LLM_CALLS_COL]
        pipeline = [
            {"$group": {
                "_id": "$model",
                "calls":       {"$sum": 1},
                "total_cost":  {"$sum": "$cost_usd"},
                "avg_latency": {"$avg": "$latency_ms"},
                "avg_conf":    {"$avg": "$result_confidence"},
                "correct":     {"$sum": {"$cond": [{"$eq": ["$was_correct", True]}, 1, 0]}},
                "hallucinations": {"$sum": {"$cond": ["$is_hallucination", 1, 0]}},
            }},
            {"$sort": {"calls": -1}},
        ]
        return list(col.aggregate(pipeline))
    except Exception:
        return []


@st.cache_data(ttl=60)
def _load_daily_cost(days: int = 30) -> list[dict]:
    db = get_db()
    if db is None:
        return []
    try:
        col = db[_LLM_CALLS_COL]
        cutoff = datetime.now(UTC) - timedelta(days=days)
        pipeline = [
            {"$match": {"created_at": {"$gte": cutoff}}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "calls":      {"$sum": 1},
                "total_cost": {"$sum": "$cost_usd"},
                "avg_latency":{"$avg": "$latency_ms"},
            }},
            {"$sort": {"_id": 1}},
        ]
        return list(col.aggregate(pipeline))
    except Exception:
        return []


@st.cache_data(ttl=60)
def _load_recent_calls(limit: int = 50) -> list[dict]:
    db = get_db()
    if db is None:
        return []
    try:
        col = db[_LLM_CALLS_COL]
        return list(col.find(
            {},
            {"pid": 1, "tcin_id": 1, "model": 1, "cost_usd": 1,
             "latency_ms": 1, "result_confidence": 1, "was_correct": 1,
             "is_hallucination": 1, "chosen_impression": 1,
             "created_at": 1, "batch_id": 1},
            sort=[("created_at", -1)],
            limit=limit
        ))
    except Exception:
        return []


# ─── Rendering helpers ─────────────────────────────────────────────────────────

def _pct(n: int, total: int) -> str:
    if total == 0:
        return "—"
    return f"{n / total:.1%}"


def _accuracy_color(rate: float) -> str:
    if rate >= 0.85:
        return "green"
    if rate >= 0.70:
        return "orange"
    return "red"


# ─── Main page ────────────────────────────────────────────────────────────────

def render():
    st.title("LLM Quality")
    st.caption("Cost, accuracy, latency, and hallucination rate for every LLM disambiguation call.")

    summary = _load_summary()
    total   = summary.get("total_calls", 0)

    if total == 0:
        st.info(
            "No LLM calls recorded yet. LLM calls are logged when the matching "
            "pipeline falls back to the LLM for low-confidence PIDs. "
            "Run the pipeline with `use_llm=true` and ThinkTank credentials configured."
        )
        return

    # ── KPI row ──────────────────────────────────────────────────────────────
    correct   = summary.get("correct_count", 0)
    incorrect = summary.get("incorrect_count", 0)
    reviewed  = correct + incorrect
    acc_rate  = correct / reviewed if reviewed > 0 else None

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Calls",        f"{total:,}")
    k2.metric("Total Cost",         f"${summary.get('total_cost', 0.0):.4f}")
    k3.metric("Avg Latency",        f"{summary.get('avg_latency_ms', 0.0):.0f} ms")
    k4.metric("Accuracy (reviewed)",
              f"{acc_rate:.1%}" if acc_rate is not None else "—",
              help=f"{correct} correct / {reviewed} reviewed")
    k5.metric("Hallucinations",
              summary.get("hallucination_count", 0),
              delta=f"{summary.get('hallucination_count', 0) / total:.1%} rate" if total else None,
              delta_color="inverse")

    st.divider()

    # ── Guardrail alerts ─────────────────────────────────────────────────────
    halluc_rate = summary.get("hallucination_count", 0) / total if total else 0
    if halluc_rate >= 0.05:
        st.error(f"CRITICAL: Hallucination rate {halluc_rate:.1%} ≥ 5% — LLM is generating impressions not in candidate list.")
    elif halluc_rate >= 0.02:
        st.warning(f"ALERT: Hallucination rate {halluc_rate:.1%} — exceeds 2% threshold. Review system prompt.")

    if acc_rate is not None and acc_rate < 0.70:
        st.error(f"CRITICAL: LLM accuracy {acc_rate:.1%} — below 70% threshold. Human reviewers rejecting >30% of LLM picks.")
    elif acc_rate is not None and acc_rate < 0.85:
        st.warning(f"WARNING: LLM accuracy {acc_rate:.1%} — below 85% target.")

    avg_lat = summary.get("avg_latency_ms", 0.0)
    if avg_lat > 5000:
        st.warning(f"ALERT: Avg LLM latency {avg_lat:.0f} ms — exceeds 5-second threshold.")

    # ── Daily cost + calls trend ─────────────────────────────────────────────
    days_back = st.slider("Trend window (days)", min_value=7, max_value=90, value=30, step=7)
    daily = _load_daily_cost(days=days_back)

    if daily:
        df_daily = pd.DataFrame([
            {"date": d["_id"], "cost_usd": d["total_cost"], "calls": d["calls"], "avg_latency_ms": d["avg_latency"]}
            for d in daily
        ]).set_index("date")

        tab_cost, tab_calls, tab_latency = st.tabs(["Daily Cost", "Daily Calls", "Avg Latency"])
        with tab_cost:
            st.bar_chart(df_daily["cost_usd"])
        with tab_calls:
            st.bar_chart(df_daily["calls"])
        with tab_latency:
            st.line_chart(df_daily["avg_latency_ms"])

    st.divider()

    # ── Per-model breakdown ───────────────────────────────────────────────────
    st.subheader("Per-Model Breakdown")
    by_model = _load_by_model()
    if by_model:
        rows = []
        for m in by_model:
            reviewed_m = m["correct"] + m.get("incorrect", 0)
            acc_m = m["correct"] / reviewed_m if reviewed_m > 0 else None
            rows.append({
                "Model":          m["_id"] or "—",
                "Calls":          m["calls"],
                "Total Cost":     f"${m['total_cost']:.4f}",
                "Cost/Call":      f"${m['total_cost'] / m['calls']:.5f}" if m["calls"] else "—",
                "Avg Latency ms": f"{m['avg_latency']:.0f}",
                "Avg Confidence": f"{m['avg_conf']:.3f}",
                "Accuracy":       f"{acc_m:.1%}" if acc_m is not None else "—",
                "Hallucinations": m["hallucinations"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()

    # ── Accuracy by batch ─────────────────────────────────────────────────────
    st.subheader("Accuracy Trend by Batch")
    db = get_db()
    if db:
        try:
            col = db[_LLM_CALLS_COL]
            batch_pipeline = [
                {"$match": {"batch_id": {"$exists": True, "$ne": None}}},
                {"$group": {
                    "_id":     "$batch_id",
                    "calls":   {"$sum": 1},
                    "correct": {"$sum": {"$cond": [{"$eq": ["$was_correct", True]}, 1, 0]}},
                    "reviewed":{"$sum": {"$cond": [{"$ne": ["$was_correct", None]}, 1, 0]}},
                    "hallucinations": {"$sum": {"$cond": ["$is_hallucination", 1, 0]}},
                    "first_call": {"$min": "$created_at"},
                }},
                {"$sort": {"first_call": -1}},
                {"$limit": 20},
            ]
            batch_rows = list(col.aggregate(batch_pipeline))
            if batch_rows:
                table = []
                for b in batch_rows:
                    rev = b["reviewed"]
                    acc = b["correct"] / rev if rev > 0 else None
                    ts  = b.get("first_call")
                    table.append({
                        "Batch":       (b["_id"] or "")[:20],
                        "Date":        ts.strftime("%Y-%m-%d") if isinstance(ts, datetime) else "—",
                        "Calls":       b["calls"],
                        "Reviewed":    rev,
                        "Accuracy":    f"{acc:.1%}" if acc is not None else "—",
                        "Hallucinations": b["hallucinations"],
                    })
                st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)
        except Exception:
            pass

    st.divider()

    # ── Recent calls table ────────────────────────────────────────────────────
    st.subheader("Recent LLM Calls")
    col_f1, col_f2 = st.columns([2, 2])
    with col_f1:
        filter_hallucs = st.checkbox("Hallucinations only", value=False)
    with col_f2:
        filter_incorrect = st.checkbox("Incorrect only", value=False)

    recent = _load_recent_calls(limit=100)
    if filter_hallucs:
        recent = [c for c in recent if c.get("is_hallucination")]
    if filter_incorrect:
        recent = [c for c in recent if c.get("was_correct") is False]

    if not recent:
        st.info("No calls match the current filters.")
    else:
        rows = []
        for c in recent[:50]:
            ts = c.get("created_at")
            correct_label = {True: "✅ Yes", False: "❌ No", None: "—"}.get(c.get("was_correct"), "—")
            rows.append({
                "PID":         c.get("pid", ""),
                "TCIN":        c.get("tcin_id", ""),
                "Model":       c.get("model", "—"),
                "Impression":  c.get("chosen_impression", "—"),
                "Confidence":  f"{c.get('result_confidence', 0.0):.3f}",
                "Cost $":      f"{c.get('cost_usd', 0.0):.5f}",
                "Latency ms":  c.get("latency_ms", 0),
                "Correct":     correct_label,
                "Hallucination": "⚠️" if c.get("is_hallucination") else "",
                "Time":        ts.strftime("%m-%d %H:%M") if isinstance(ts, datetime) else "—",
            })
        df = pd.DataFrame(rows)

        def _color_row(row):
            if "⚠️" in row.get("Hallucination", ""):
                return ["background-color: #ffeaa7"] * len(row)
            if row.get("Correct") == "❌ No":
                return ["background-color: #fab1a0"] * len(row)
            return [""] * len(row)

        st.dataframe(
            df.style.apply(_color_row, axis=1),
            use_container_width=True,
            hide_index=True,
        )

    # ── Cost projection ───────────────────────────────────────────────────────
    with st.expander("Cost Projection", expanded=False):
        if daily:
            recent_days = daily[-7:] if len(daily) >= 7 else daily
            avg_daily = sum(d["total_cost"] for d in recent_days) / len(recent_days)
            st.write(f"**Avg daily cost (last {len(recent_days)} days):** ${avg_daily:.4f}")
            st.write(f"**Projected monthly cost:** ${avg_daily * 30:.2f}")
            st.write(f"**Projected annual cost:** ${avg_daily * 365:.2f}")
            avg_calls = sum(d["calls"] for d in recent_days) / len(recent_days)
            st.caption(f"Based on {avg_calls:.0f} calls/day average")
        else:
            st.info("Not enough data for projection.")


if __name__ == "__main__":
    render()
