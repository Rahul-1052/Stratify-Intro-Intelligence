import streamlit as st
from core.stratify_report import run_stratify_report

from version import (
    STRATIFY_VERSION,
    INTRO_ENGINE,
    PATTERN_ENGINE,
    BENCHMARK_ENGINE,
    RECOMMENDATION_ENGINE,
)


DEBUG = False

st.set_page_config(page_title="Stratify 2.0", layout="wide")

st.title("Stratify 2.0")
st.caption("Evidence-first creator intelligence")

url = st.text_input("Paste YouTube Video URL")
analyze_clicked = st.button("Build Stratify Report", width="stretch")


def render_empty(message="No evidence available yet."):
    st.write(message)


def render_feature_rows(feature_comparison):
    if not feature_comparison:
        render_empty()
        return

    for item in feature_comparison:
        st.write(f"**{item.get('label', 'Feature').title()}**")
        st.write(f"User intro: {item.get('user_value', 'unknown')}")
        st.write(item.get("top_evidence", "Top performers: no evidence available."))
        st.write(item.get("lower_evidence", "Lower performers: no evidence available."))
        st.write(f"Position: {item.get('status', 'insufficient_evidence')}")
        st.caption(item.get("explanation", "No comparison explanation available."))


def render_position(items):
    if not items:
        render_empty("Stratify could not confidently position this intro yet.")
        return

    for item in items:
        st.write(f"- {item}")


def render_signal_list(items, empty_message):
    if not items:
        render_empty(empty_message)
        return

    for item in items:
        label = item.get("label", "Feature").title()
        user_value = item.get("user_value", "unknown")
        top_value = item.get("top_dominant_value", "unknown")
        lower_value = item.get("lower_dominant_value")

        st.write(f"**{label}**")
        st.write(f"User intro: {user_value}")
        st.write(f"Dominant top performer value: {top_value}")

        if lower_value:
            st.write(f"Dominant lower performer value: {lower_value}")

        st.caption(item.get("explanation", "No comparison explanation available."))


if analyze_clicked:
    if not url.strip():
        st.warning("Paste a YouTube URL.")
        st.stop()

    with st.status("Building your Stratify report...", expanded=True) as status:
        def show_progress(message):
            st.write(message)

        report = run_stratify_report(
            url.strip(),
            intro_seconds=15,
            frame_fps=1,
            progress_callback=show_progress,
        )

        if report["status"] == "failed":
            status.update(
                label="Stratify could not build this report.",
                state="error",
                expanded=True,
            )

            for warning in report.get("warnings", []):
                st.error(warning)

            st.stop()

        status.update(
            label=(
                "Partial Stratify report ready."
                if report["status"] == "partial"
                else "Stratify report ready."
            ),
            state="complete",
            expanded=False,
        )

    feature_report = report.get("feature_report", {})
    category = report.get("category", {})
    benchmark = report.get("benchmark", {})
    benchmark_features = report.get("benchmark_features", {})
    patterns = report.get("patterns", {})

    if report.get("warnings"):
        st.warning(
            "Stratify built the best available report, but one part of the intro pipeline had an issue."
        )

        with st.expander("What happened?"):
            for warning in report["warnings"]:
                st.write(f"- {warning}")

    # =====================================================
    # BENCHMARK DISCOVERY
    # =====================================================

    st.header("Benchmark Discovery")

    st.subheader("Detected Search Context")
    st.write(category.get("search_query", "No search context detected yet."))

    search_queries = category.get("search_queries", [])
    if search_queries:
        st.subheader("Search Queries")
        for query in search_queries:
            st.write(f"- {query}")

    top_performers = benchmark.get("top_performers", [])
    lower_performers = benchmark.get("lower_performers", [])

    st.subheader("Top Performers Found")
    if top_performers:
        for video_item in top_performers:
            st.write(
                f"- {video_item.get('title')} "
                f"({video_item.get('views', 0):,} views)"
            )
    else:
        render_empty("No relevant top performers found.")

    st.subheader("Lower Performers Found")
    if lower_performers:
        for video_item in lower_performers:
            st.write(
                f"- {video_item.get('title')} "
                f"({video_item.get('views', 0):,} views)"
            )
    else:
        render_empty("No reliable lower-performer comparison set found.")

    st.subheader("Benchmark Intros Analyzed")
    st.write(
        f"Top performer intros analyzed: "
        f"{len(benchmark_features.get('top_performers', []))}"
    )
    st.write(
        f"Lower performer intros analyzed: "
        f"{len(benchmark_features.get('lower_performers', []))}"
    )

    st.divider()

    # =====================================================
    # INTRO FEATURE EVIDENCE
    # =====================================================

    st.header("Intro Feature Evidence")

    feature_summary = feature_report.get("feature_summary", {})

    st.subheader("Extracted User Intro Evidence")
    st.write(f"Frames analyzed: {feature_summary.get('frames_analyzed', 'unknown')}")
    st.write(f"Dominant lighting: {feature_summary.get('dominant_lighting', 'unknown')}")
    st.write(
        f"Dominant color feel: "
        f"{feature_summary.get('dominant_color_feel', 'unknown')}"
    )
    st.write(f"Human presence: {feature_summary.get('human_presence', 'unknown')}")
    st.write(f"Text overlay: {feature_summary.get('text_overlay', 'unknown')}")
    st.write(f"Scene type: {feature_summary.get('scene_type', 'unknown')}")
    st.write(f"Visual energy: {feature_summary.get('visual_energy', 'unknown')}")

    with st.expander("See benchmark feature comparison"):
        render_feature_rows(patterns.get("feature_comparison", []))

    st.divider()

    # =====================================================
    # YOUR INTRO POSITION
    # =====================================================

    st.header("Your Intro Position")
    render_position(patterns.get("user_position", []))

    st.divider()

    # =====================================================
    # MISSING WINNING FEATURES
    # =====================================================

    st.header("Missing Winning Features")
    render_signal_list(
        patterns.get("missing_winning_features", []),
        "No missing winning features were identified from the current evidence.",
    )

    st.divider()

    # =====================================================
    # RISK SIGNALS
    # =====================================================

    st.header("Risk Signals")
    render_signal_list(
        patterns.get("risk_signals", []),
        "No risk signals were identified from the current evidence.",
    )

    st.divider()

    # =====================================================
    # FINAL VERDICT
    # =====================================================

    st.header("Final Verdict")
    st.write(
        patterns.get(
            "final_verdict",
            "Stratify does not have enough evidence to position this intro yet.",
        )
    )

    st.divider()

    # =====================================================
    # EVIDENCE CONFIDENCE
    # =====================================================

    st.header("Evidence Confidence")
    st.write(f"Confidence: {patterns.get('confidence', 'low').title()}")
    st.write(
        patterns.get(
            "confidence_reason",
            "Not enough benchmark intro evidence was available.",
        )
    )

    if DEBUG:
        with st.expander("Developer Mode"):
            st.write(report)

    st.divider()

    st.caption(
        f"""
    Stratify {STRATIFY_VERSION}
    |
    {INTRO_ENGINE}
    |
    {PATTERN_ENGINE}
    |
    {BENCHMARK_ENGINE}
    |
    {RECOMMENDATION_ENGINE}
    """
    )