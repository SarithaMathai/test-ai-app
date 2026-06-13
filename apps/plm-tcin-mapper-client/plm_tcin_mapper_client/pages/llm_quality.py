"""LLM Quality — Streamlit page.

Shows cost, accuracy, latency, and hallucination rate for LLM calls via the API.
"""

from __future__ import annotations

from typing import Any

import httpx
import pandas as pd
import streamlit as st

from plm_tcin_mapper_client import api_client


# ─── Data loaders ─────────────────────────────────────────────────────────────


@st.cache_data(ttl=60)
def _load_summary() -> dict[str, Any]:
    """Load LLM quality metrics via API."""
    try:
        result = api_client.get_llm_quality()
        return result.get("summary", {})
    except httpx.HTTPError:
        return {}


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
    st.caption("Cost, accuracy, latency, and hallucination rate for LLM disambiguation calls.")

    summary = _load_summary()
    total = summary.get("total_calls", 0)

    if total == 0:
        st.info(
            "No LLM calls recorded yet. LLM calls are logged when the matching "
            "pipeline falls back to the LLM for low-confidence PIDs. "
            "Run the pipeline with `use_llm=true` and model credentials configured."
        )
        return

    # ── KPI row ──────────────────────────────────────────────────────────────
    correct = summary.get("correct_count", 0)
    incorrect = summary.get("incorrect_count", 0)
    reviewed = correct + incorrect
    acc_rate = correct / reviewed if reviewed > 0 else None

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Calls", f"{total:,}")
    k2.metric("Total Cost", f"${summary.get('total_cost', 0.0):.4f}")
    k3.metric("Avg Latency", f"{summary.get('avg_latency_ms', 0.0):.0f} ms")
    k4.metric(
        "Accuracy (reviewed)",
        f"{acc_rate:.1%}" if acc_rate is not None else "—",
        help=f"{correct} correct / {reviewed} reviewed",
    )
    k5.metric(
        "Hallucinations",
        summary.get("hallucination_count", 0),
        delta=f"{summary.get('hallucination_count', 0) / total:.1%} rate" if total else None,
        delta_color="inverse",
    )

    st.divider()

    # ── Guardrail alerts ─────────────────────────────────────────────────────
    halluc_rate = summary.get("hallucination_count", 0) / total if total else 0
    if halluc_rate >= 0.05:
        st.error(
            f"CRITICAL: Hallucination rate {halluc_rate:.1%} ≥ 5% — LLM is generating impressions not in candidate list."
        )
    elif halluc_rate >= 0.02:
        st.warning(f"ALERT: Hallucination rate {halluc_rate:.1%} — exceeds 2% threshold. Review system prompt.")

    if acc_rate is not None and acc_rate < 0.70:
        st.error(
            f"CRITICAL: LLM accuracy {acc_rate:.1%} — below 70% threshold. Human reviewers rejecting >30% of LLM picks."
        )
    elif acc_rate is not None and acc_rate < 0.85:
        st.warning(f"WARNING: LLM accuracy {acc_rate:.1%} — below 85% target.")

    avg_lat = summary.get("avg_latency_ms", 0.0)
    if avg_lat > 5000:
        st.warning(f"ALERT: Avg LLM latency {avg_lat:.0f} ms — exceeds 5-second threshold.")

    st.divider()

    # ── Per-model breakdown ───────────────────────────────────────────────────
    st.subheader("Per-Model Breakdown")
    by_model = summary.get("by_model", [])
    if by_model:
        rows = []
        for m in by_model:
            reviewed_m = m.get("correct", 0) + m.get("incorrect", 0)
            acc_m = m.get("correct", 0) / reviewed_m if reviewed_m > 0 else None
            rows.append(
                {
                    "Model": m.get("model", "—"),
                    "Calls": m.get("calls", 0),
                    "Total Cost": f"${m.get('total_cost', 0.0):.4f}",
                    "Cost/Call": f"${m.get('total_cost', 0.0) / m.get('calls', 1):.5f}" if m.get("calls") else "—",
                    "Avg Latency ms": f"{m.get('avg_latency', 0):.0f}",
                    "Avg Confidence": f"{m.get('avg_confidence', 0):.3f}",
                    "Accuracy": f"{acc_m:.1%}" if acc_m is not None else "—",
                    "Hallucinations": m.get("hallucinations", 0),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()

    # ── Recent calls table ────────────────────────────────────────────────────
    st.subheader("Recent LLM Calls")
    col_f1, col_f2 = st.columns([2, 2])
    with col_f1:
        filter_hallucs = st.checkbox("Hallucinations only", value=False)
    with col_f2:
        filter_incorrect = st.checkbox("Incorrect only", value=False)

    recent = summary.get("recent_calls", [])
    if filter_hallucs:
        recent = [c for c in recent if c.get("is_hallucination")]
    if filter_incorrect:
        recent = [c for c in recent if c.get("was_correct") is False]

    if not recent:
        st.info("No calls match the current filters.")
    else:
        rows = []
        for c in recent[:50]:
            correct_label = {True: "✅ Yes", False: "❌ No", None: "—"}.get(c.get("was_correct"), "—")
            rows.append(
                {
                    "PID": c.get("pid", ""),
                    "TCIN": c.get("tcin_id", ""),
                    "Model": c.get("model", "—"),
                    "Impression": c.get("chosen_impression", "—"),
                    "Confidence": f"{c.get('result_confidence', 0.0):.3f}",
                    "Cost $": f"{c.get('cost_usd', 0.0):.5f}",
                    "Latency ms": c.get("latency_ms", 0),
                    "Correct": correct_label,
                    "Hallucination": "⚠️" if c.get("is_hallucination") else "",
                }
            )
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

    st.divider()

    # ── Cost projection ───────────────────────────────────────────────────────
    with st.expander("Cost Projection", expanded=False):
        total_cost = summary.get("total_cost", 0)
        if total_cost and total > 0:
            avg_cost_per_call = total_cost / total
            st.write(f"**Total cost to date:** ${total_cost:.4f}")
            st.write(f"**Average cost per call:** ${avg_cost_per_call:.5f}")
            st.write(f"**Projected monthly cost (at current rate):** ${avg_cost_per_call * 1000 * 30:.2f}")
            st.write(f"**Projected annual cost (at current rate):** ${avg_cost_per_call * 1000 * 365:.2f}")
            st.caption(f"Based on {total} calls recorded")
        else:
            st.info("Not enough data for projection.")


if __name__ == "__main__":
    render()
