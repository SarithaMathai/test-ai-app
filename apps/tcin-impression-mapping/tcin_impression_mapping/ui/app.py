"""Streamlit UI for TCIN impression mapping.

Usage:
  make run-tcin
  # or: uv run streamlit run apps/tcin-impression-mapping/tcin_impression_mapping/ui/app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
from ai_core.config import get_settings
from ai_core.llm.factory import build_llm_client

from tcin_impression_mapping.models.schemas import MappingRequest, MatchStrategy
from tcin_impression_mapping.services.mapper import MapperService

# ── page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="TCIN Impression Mapper",
    page_icon="🎨",
    layout="wide",
)


# ── singleton resources ───────────────────────────────────────────────────────


@st.cache_resource
def _get_mapper() -> MapperService:
    settings = get_settings()
    llm = build_llm_client(settings)
    return MapperService(llm)


def _confidence_badge(confidence: float, strategy: str) -> str:
    if strategy == MatchStrategy.NO_MATCH:
        return "🔴 No Match"
    if confidence >= 0.85:
        return f"🟢 {confidence:.0%}"
    if confidence >= 0.60:
        return f"🟡 {confidence:.0%}"
    return f"🔴 {confidence:.0%}"


# ── sidebar: config info ──────────────────────────────────────────────────────

with st.sidebar:
    st.header("Configuration")
    try:
        settings = get_settings()
        st.info(f"**Provider:** {settings.llm.provider}\n\n**Model:** {settings.llm.model}")
        st.caption("Auto-accept threshold: 85% | LLM fallback: 60%")
    except Exception as e:
        st.error(f"Config error: {e}")

    st.divider()
    st.markdown("""
**Confidence legend**
- 🟢 ≥ 85% — auto-accepted
- 🟡 60-84% — LLM assisted
- 🔴 < 60% — needs review
""")


# ── main UI ───────────────────────────────────────────────────────────────────

st.title("🎨 TCIN Impression Mapper")
st.caption("Deterministic fuzzy matching with LLM fallback for ambiguous cases.")

tab_single, tab_batch = st.tabs(["Single mapping", "Batch CSV"])

# ── tab 1: single mapping ────────────────────────────────────────────────────

with tab_single:
    st.subheader("Map one TCIN color")
    col1, col2 = st.columns(2)

    with col1:
        pid = st.text_input("PID", value="12345678")
        tcin_id = st.text_input("TCIN ID", value="87654321")
        color_family = st.text_input("Color family", value="Blue")
        color_name = st.text_input("Color name", value="Navy Blue")
        size = st.text_input("Size", value="M")

    with col2:
        candidates_raw = st.text_area(
            "Impression candidates (one per line)",
            value="NAVY\nDARK BLUE\nCOBALT DREAM\nROYAL BLUE\nMIDNIGHT",
            height=180,
        )

    if st.button("Map", type="primary"):
        candidates = [c.strip() for c in candidates_raw.splitlines() if c.strip()]
        if not candidates:
            st.warning("Enter at least one candidate impression.")
        else:
            with st.spinner("Mapping…"):
                try:
                    mapper = _get_mapper()
                    result = mapper.map_one(
                        MappingRequest(
                            pid=pid,
                            tcin_id=tcin_id,
                            color_family=color_family,
                            color_name=color_name,
                            size=size,
                            candidates=candidates,
                        )
                    )
                    st.success(f"**Match:** {result.chosen_impression}")
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Confidence", f"{result.confidence:.0%}")
                    col_b.metric("Strategy", result.strategy.value)
                    col_c.metric("Badge", _confidence_badge(result.confidence, result.strategy))
                    st.caption(f"Reasoning: {result.reasoning}")
                    if result.needs_review:
                        st.warning("⚠️ This result needs human review.")
                except Exception as exc:
                    st.error(f"Mapping failed: {exc}")


# ── tab 2: batch CSV ─────────────────────────────────────────────────────────

with tab_batch:
    st.subheader("Batch mapping from CSV")
    st.caption(
        "Upload a CSV with columns: pid, tcin_id, color_family, color_name, size, candidates "
        "(candidates = pipe-separated impression names)."
    )

    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded:
        try:
            df = pd.read_csv(uploaded)
            required = {"pid", "tcin_id", "color_family", "color_name", "size", "candidates"}
            missing = required - set(df.columns)
            if missing:
                st.error(f"Missing columns: {missing}")
            else:
                st.dataframe(df.head(5), use_container_width=True)
                if st.button("Run batch mapping", type="primary"):
                    requests = [
                        MappingRequest(
                            pid=str(row["pid"]),
                            tcin_id=str(row["tcin_id"]),
                            color_family=str(row["color_family"]),
                            color_name=str(row["color_name"]),
                            size=str(row["size"]),
                            candidates=[
                                c.strip() for c in str(row["candidates"]).split("|") if c.strip()
                            ],
                        )
                        for _, row in df.iterrows()
                    ]

                    progress = st.progress(0, text="Mapping…")
                    mapper = _get_mapper()
                    results_data = []
                    for i, req in enumerate(requests):
                        res = mapper.map_one(req)
                        results_data.append(
                            {
                                "pid": res.pid,
                                "tcin_id": res.tcin_id,
                                "color_name": res.color_name,
                                "chosen_impression": res.chosen_impression,
                                "confidence": f"{res.confidence:.0%}",
                                "strategy": res.strategy.value,
                                "needs_review": res.needs_review,
                                "reasoning": res.reasoning,
                            }
                        )
                        progress.progress((i + 1) / len(requests), text=f"{i + 1}/{len(requests)}")

                    progress.empty()
                    results_df = pd.DataFrame(results_data)
                    needs_review = results_df["needs_review"].sum()

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total", len(results_df))
                    col2.metric("Needs review", int(needs_review))
                    col3.metric(
                        "Auto-accepted",
                        int((results_df["strategy"] == "deterministic").sum()),
                    )

                    st.dataframe(
                        results_df.style.apply(
                            lambda row: [
                                "background-color: #fff3cd" if row["needs_review"] else ""
                                for _ in row
                            ],
                            axis=1,
                        ),
                        use_container_width=True,
                    )

                    csv_out = results_df.to_csv(index=False)
                    st.download_button(
                        "Download results CSV", csv_out, "mapping_results.csv", "text/csv"
                    )

        except Exception as exc:
            st.error(f"Error: {exc}")


def launch() -> None:
    """Entry point for `tcin-ui` CLI script — runs streamlit programmatically."""
    import sys

    from streamlit.web import cli as stcli

    sys.argv = ["streamlit", "run", __file__, "--server.headless", "true"]
    stcli.main()
