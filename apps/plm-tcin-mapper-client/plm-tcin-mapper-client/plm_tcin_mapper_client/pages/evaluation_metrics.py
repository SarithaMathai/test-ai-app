"""Evaluation Metrics — Streamlit page.

Shows detailed accuracy metrics by signal type, department, LLM impact, and confidence calibration.
Provides diagnostic insights for algorithm improvement and troubleshooting.
"""

from __future__ import annotations

from typing import Any

import httpx
import pandas as pd
import streamlit as st
from plm_tcin_mapper_client import api_client

# ─── Data loaders ─────────────────────────────────────────────────────────────


@st.cache_data(ttl=300)
def _load_latest_extended_eval() -> dict[str, Any] | None:
    """Load the most recent extended evaluation run via API."""
    try:
        result = api_client.get_eval_detailed_latest()
        # API returns the eval object directly (or null → None when no eval exists yet)
        return result if isinstance(result, dict) else None
    except httpx.HTTPError:
        return None


# ─── Render functions ─────────────────────────────────────────────────────────


def render():
    """Main page rendering function."""
    st.title("🎯 Evaluation Metrics")
    st.markdown("Detailed accuracy analysis: per-signal, per-department, LLM impact, and confidence calibration.")

    # Control bar
    col1, col2, _col3 = st.columns([2, 3, 3])
    with col1:
        run_fresh = st.button("▶ Run Fresh Eval", type="primary")
        if run_fresh:
            with st.spinner("Computing evaluation metrics…"):
                try:
                    api_client.run_eval_detailed()
                    st.success("Evaluation complete!")
                    _load_latest_extended_eval.clear()
                except httpx.HTTPError as e:
                    st.error(f"Eval failed: {e}")
    with col2:
        st.caption("Run a fresh evaluation to update metrics from the current mappings collection.")

    st.divider()

    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📊 Overview",
            "🔧 Per-Signal Analysis",
            "🏢 Per-Department Analysis",
            "🤖 LLM Impact",
            "📈 Trend",
        ]
    )

    with tab1:
        _render_overview()

    with tab2:
        _render_per_signal_analysis()

    with tab3:
        _render_per_department_analysis()

    with tab4:
        _render_llm_impact()

    with tab5:
        _render_trend()


def _render_overview():
    """Render overall evaluation summary."""
    eval_run = _load_latest_extended_eval()

    if not eval_run:
        st.info("No evaluation data available. Click 'Run Fresh Eval' to generate metrics.")
        return

    # Display basic stats
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Total Mappings",
            f"{eval_run.get('total_mappings', 0):,}",
        )

    with col2:
        st.metric(
            "Correction Rate",
            f"{eval_run.get('correction_rate', 0):.1%}",
            delta="↓ Better" if eval_run.get("correction_rate", 1.0) < 0.30 else "↑ Worse",
        )

    with col3:
        st.metric(
            "Avg Confidence",
            f"{eval_run.get('avg_color_confidence', 0):.3f}",
        )

    with col4:
        st.metric(
            "HIGH Tier %",
            f"{eval_run.get('pct_high', 0):.1%}",
            delta="↑ Better" if eval_run.get("pct_high", 0) > 0.40 else "↓ Lower",
        )

    with col5:
        st.metric(
            "Calibration Error",
            f"{eval_run.get('confidence_calibration_error', 0):.3f}",
            delta="↓ Better (Well-calibrated)"
            if eval_run.get("confidence_calibration_error", 1.0) < 0.10
            else "↑ Worse",
        )

    st.divider()

    # Detailed status breakdown
    st.subheader("Status Distribution")
    by_status = eval_run.get("by_status", {})
    by_tier = eval_run.get("by_tier", {})

    col1, col2 = st.columns(2)

    with col1:
        if by_status:
            st.bar_chart(by_status)
        st.caption("Mappings by status")

    with col2:
        if by_tier:
            st.bar_chart(by_tier)
        st.caption("Mappings by confidence tier")

    # Guardrail alerts
    alerts = eval_run.get("guardrail_alerts", [])
    if alerts:
        st.warning("⚠️ **Guardrail Alerts**")
        for alert in alerts:
            st.write(f"• {alert}")

    # Confidence rates
    st.subheader("Confidence vs Actual Error")
    col1, col2 = st.columns(2)

    with col1:
        high_correction = eval_run.get("high_confidence_actual_correction_rate", 0)
        st.metric(
            "HIGH Confidence Actual Correction Rate",
            f"{high_correction:.1%}",
            delta="↓ Better (should be <15%)"
            if high_correction < 0.15
            else "❌ Issues"
            if high_correction > 0.25
            else "✓ OK",
        )
        st.caption("% of HIGH-confidence mappings that were corrected by reviewers")

    with col2:
        low_correction = eval_run.get("low_confidence_actual_correction_rate", 0)
        st.metric(
            "LOW Confidence Actual Correction Rate",
            f"{low_correction:.1%}",
            delta="✓ Expected (50-80%)" if 0.50 <= low_correction <= 0.80 else "⚠️ Unexpected",
        )
        st.caption("% of LOW-confidence mappings that were corrected by reviewers")


def _render_per_signal_analysis():
    """Render per-signal accuracy breakdown."""
    eval_run = _load_latest_extended_eval()

    if not eval_run:
        st.info("No evaluation data available.")
        return

    st.subheader("Scoring Signal Accuracy")
    st.markdown("How accurate is each scoring signal? Higher correction_rate = weaker signal.")

    per_signal = eval_run.get("per_signal_accuracy", {})

    if not per_signal:
        st.info("No per-signal data available.")
        return

    # Create comparison table
    signal_data = []
    for signal_type, metrics in per_signal.items():
        signal_data.append(
            {
                "Signal": signal_type,
                "Occurrences": metrics.get("occurrences", 0),
                "Corrections": metrics.get("corrections", 0),
                "Correction Rate": f"{metrics.get('correction_rate', 0):.1%}",
                "Avg Confidence": f"{metrics.get('avg_confidence', 0):.3f}",
            }
        )

    df = pd.DataFrame(signal_data)
    st.dataframe(df, use_container_width=True)

    # Signal health indicators
    st.subheader("Signal Health")
    cols = st.columns(len(per_signal))

    for col, (signal_type, metrics) in zip(cols, per_signal.items(), strict=False):
        correction_rate = metrics.get("correction_rate", 0)

        if correction_rate < 0.20:
            status = "✅ Strong"
        elif correction_rate < 0.35:
            status = "✓ Good"
        elif correction_rate < 0.50:
            status = "⚠️ Weak"
        else:
            status = "❌ Very Weak"

        with col:
            st.metric(
                signal_type,
                f"{correction_rate:.1%}",
                delta=status,
            )
            st.caption(f"Count: {metrics.get('occurrences', 0)}")

    # Detailed recommendations
    st.subheader("Recommendations")

    weakest_signal = max(per_signal.items(), key=lambda x: x[1].get("correction_rate", 0))
    if weakest_signal[1].get("correction_rate", 0) > 0.40:
        st.warning(
            f"⚠️ **{weakest_signal[0].upper()} signal is weak** "
            f"({weakest_signal[1].get('correction_rate', 0):.1%} correction rate). "
            "Consider: "
            "1) Running alias mining to improve keyword coverage, or "
            "2) Reducing the weight of this signal in the scorer, or "
            "3) Investigating data quality issues."
        )

    strongest_signal = min(per_signal.items(), key=lambda x: x[1].get("correction_rate", 0))
    st.success(
        f"✅ **{strongest_signal[0].upper()} signal is strong** "
        f"({strongest_signal[1].get('correction_rate', 0):.1%} correction rate). "
        "Prioritize mappings using this signal."
    )


def _render_per_department_analysis():
    """Render per-department accuracy breakdown."""
    eval_run = _load_latest_extended_eval()

    if not eval_run:
        st.info("No evaluation data available.")
        return

    st.subheader("Department/Family Accuracy")
    st.markdown("Accuracy varies by product department. Identify departments that need focused improvement.")

    per_dept = eval_run.get("per_department_metrics", [])

    if not per_dept:
        st.info("No per-department data available.")
        return

    # Create comparison table
    dept_data = []
    for metric in per_dept:
        dept_data.append(
            {
                "Department": metric.get("department", "unknown"),
                "Total": metric.get("total_mappings", 0),
                "HIGH %": f"{metric.get('pct_high_confidence', 0):.1%}",
                "Correction Rate": f"{metric.get('correction_rate', 0):.1%}",
                "Avg Confidence": f"{metric.get('avg_confidence', 0):.3f}",
            }
        )

    df = pd.DataFrame(dept_data)
    st.dataframe(df, use_container_width=True)

    # Department health indicators
    st.subheader("Department Health")
    cols = st.columns(min(3, len(per_dept)))

    for col, metric in zip(cols, per_dept, strict=False):
        correction_rate = metric.get("correction_rate", 0)

        if correction_rate < 0.20:
            status = "✅ Excellent"
        elif correction_rate < 0.30:
            status = "✓ Good"
        elif correction_rate < 0.40:
            status = "⚠️ Needs Work"
        else:
            status = "❌ Critical"

        with col:
            st.metric(
                metric.get("department", "unknown"),
                f"{correction_rate:.1%}",
                delta=status,
            )
            st.caption(f"Total: {metric.get('total_mappings', 0)}")

    # Department-specific recommendations
    st.subheader("Recommendations")

    problem_depts = [m for m in per_dept if m.get("correction_rate", 0) > 0.35]
    if problem_depts:
        st.warning(f"⚠️ **{len(problem_depts)} department(s) have high error rates:**")
        for dept in problem_depts:
            st.markdown(
                f"• **{dept.get('department', 'unknown')}**: "
                f"{dept.get('correction_rate', 0):.1%} correction rate. "
                f"Run alias mining to identify missing keywords for this category."
            )


def _render_llm_impact():
    """Render LLM vs deterministic analysis."""
    eval_run = _load_latest_extended_eval()

    if not eval_run:
        st.info("No evaluation data available.")
        return

    st.subheader("LLM Impact Analysis")
    st.markdown("Compare LLM-assisted matching vs pure deterministic to see if LLM is helping.")

    llm_impact = eval_run.get("llm_impact")

    if not llm_impact:
        st.info("No LLM impact data (likely no LLM calls in this batch).")
        return

    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "LLM Calls",
            f"{llm_impact.get('total_llm_calls', 0):,}",
        )

    with col2:
        st.metric(
            "LLM Correction Rate",
            f"{llm_impact.get('llm_correction_rate', 0):.1%}",
        )

    with col3:
        st.metric(
            "Deterministic Correction Rate",
            f"{llm_impact.get('deterministic_correction_rate', 0):.1%}",
        )

    with col4:
        improvement = llm_impact.get("llm_vs_deterministic_improvement", 0)
        st.metric(
            "LLM Improvement",
            f"{improvement:+.1%}",
            delta="✅ Helping" if improvement > 0.05 else "⚠️ Neutral" if abs(improvement) < 0.05 else "❌ Hurting",
        )

    st.divider()

    # Detailed comparison
    st.subheader("Detailed Comparison")

    comparison_data = {
        "Metric": [
            "Total Calls/Matches",
            "Corrections",
            "Correction Rate",
            "Avg Confidence",
        ],
        "LLM": [
            f"{llm_impact.get('total_llm_calls', 0)}",
            f"{llm_impact.get('llm_corrected', 0)}",
            f"{llm_impact.get('llm_correction_rate', 0):.1%}",
            f"{llm_impact.get('llm_avg_confidence', 0):.3f}",
        ],
        "Deterministic": [
            f"{eval_run.get('total_mappings', 0) - llm_impact.get('total_llm_calls', 0)}",
            f"{llm_impact.get('deterministic_corrected', 0)}",
            f"{llm_impact.get('deterministic_correction_rate', 0):.1%}",
            "—",
        ],
    }

    df = pd.DataFrame(comparison_data)
    st.dataframe(df, use_container_width=True)

    # Recommendations
    st.subheader("Recommendations")

    improvement = llm_impact.get("llm_vs_deterministic_improvement", 0)

    if improvement > 0.10:
        st.success(
            f"✅ **LLM is significantly helping** ({improvement:+.1%} improvement). "
            "Consider lowering the LLM fallback threshold to catch more ambiguous cases."
        )
    elif improvement > 0.05:
        st.info(f"✓ **LLM is moderately helpful** ({improvement:+.1%} improvement). Current setup is working well.")
    elif improvement > -0.05:
        st.warning(
            f"⚠️ **LLM impact is neutral** ({improvement:+.1%}). "
            "Consider reviewing LLM prompts or JSON parsing for errors."
        )
    else:
        st.error(
            f"❌ **LLM is hurting performance** ({improvement:+.1%} worse). "
            "Review LLM configuration and consider disabling until fixed."
        )


def _render_trend():
    """Render confidence and quality trends over recent eval runs."""
    st.subheader("Metrics Trend")
    st.markdown("Trend analysis requires running fresh evaluations over time. Check back after multiple runs!")
    st.info("Trend data will be available after collecting multiple evaluation runs.")
