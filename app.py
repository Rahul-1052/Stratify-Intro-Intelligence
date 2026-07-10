import os

import streamlit as st

from core.stratify_report import run_stratify_report
from version import (
    BENCHMARK_ENGINE,
    INTRO_ENGINE,
    PATTERN_ENGINE,
    PRODUCT_MODE,
    RECOMMENDATION_ENGINE,
    STRATIFY_VERSION,
)


ACTIVE_PRODUCT_MODE = os.getenv("STRATIFY_PRODUCT_MODE", PRODUCT_MODE).strip().lower()
if ACTIVE_PRODUCT_MODE not in {"builder", "creator"}:
    ACTIVE_PRODUCT_MODE = "builder"

DEBUG = (
    ACTIVE_PRODUCT_MODE == "builder"
    and os.getenv("STRATIFY_DEBUG", "false").strip().lower() == "true"
)

YOUTUBE_BLOCK_FALLBACK = (
    "YouTube blocked automated access before Stratify could analyze the intro. "
    "Try this URL again later or use another publicly accessible YouTube video. "
    "Stratify will still use any benchmark evidence that is available."
)

STATUS_LABELS = {
    "aligned_with_top": "Already matches strong videos",
    "missing_winning_feature": "Worth testing",
    "risk_signal": "Worth testing",
    "non_discriminative": "Common in both groups",
    "insufficient_evidence": "Not enough evidence yet",
    "observed_alignment": "Observed in strong videos",
    "observed_difference": "Different from strong videos",
}

st.set_page_config(page_title=f"Stratify {STRATIFY_VERSION}", layout="wide")
st.title("Stratify 2.0")
st.caption("Evidence-first creator intelligence")
st.caption(
    f"v{STRATIFY_VERSION} | {INTRO_ENGINE} | {ACTIVE_PRODUCT_MODE.title()} mode"
)

url = st.text_input("Paste YouTube Video URL")
analyze_clicked = st.button("Build Stratify Report", width="stretch")


def render_empty(message="No evidence available yet."):
    st.write(message)


def has_youtube_download_block(warnings):
    block_markers = (
        "yt_dlp_download_failed",
        "yt-dlp",
        "sign in to confirm you're not a bot",
        "sign in to confirm you’re not a bot",
        "youtube bot blocking",
        "http error 403",
        "forbidden",
    )
    warning_text = " ".join(str(warning).lower() for warning in warnings or [])
    return any(marker in warning_text for marker in block_markers)


def count_analyzed_intros(items):
    return sum(
        bool(item.get("features", {}).get("feature_summary", {}))
        for item in items or []
        if isinstance(item, dict)
    )


def human_status(status):
    return STATUS_LABELS.get(status, str(status or "Not enough evidence yet"))


def first_sentence(text):
    cleaned = str(text or "").strip()
    if not cleaned:
        return "This is the strongest evidence-backed test Stratify found."
    for marker in (". ", "? ", "! "):
        if marker in cleaned:
            return cleaned.split(marker, 1)[0].strip() + marker.strip()
    return cleaned


def strongest_recommendation(patterns):
    experiments = patterns.get("top_creator_experiments", [])
    recommendations = patterns.get("recommendations", [])
    if experiments:
        return experiments[0]
    if recommendations:
        return recommendations[0]
    return {}


def render_intro_values(feature_summary):
    st.write(f"Frames analyzed: {feature_summary.get('frames_analyzed', 'unknown')}")
    st.write(
        f"Lighting: {feature_summary.get('dominant_lighting', 'unknown')}"
    )
    st.write(
        f"Color feel: {feature_summary.get('dominant_color_feel', 'unknown')}"
    )
    st.write(f"Motion level: {feature_summary.get('motion_level', 'unknown')}")
    st.write(
        f"Scene changes detected: "
        f"{feature_summary.get('scene_change_count', 'unknown')}"
    )
    st.write(f"Pacing level: {feature_summary.get('pacing_level', 'unknown')}")
    st.write(f"Visual energy: {feature_summary.get('visual_energy', 'unknown')}")
    st.write(f"Human presence: {feature_summary.get('human_presence', 'unknown')}")
    st.write(f"Text overlay: {feature_summary.get('text_overlay', 'unknown')}")
    st.write(f"Scene type: {feature_summary.get('scene_type', 'unknown')}")


def render_storytelling_values(feature_summary):
    st.write(
        "First Frame Strength: "
        f"{feature_summary.get('first_frame_strength', 'unknown')}"
    )
    st.write(
        "Opening Action Type: "
        f"{feature_summary.get('opening_action_type', 'unknown')}"
    )
    st.write(
        "Hook Visible in First 3 Seconds: "
        f"{feature_summary.get('hook_visible_in_first_3_seconds', 'unknown')}"
    )
    st.write(f"Subject Clarity: {feature_summary.get('subject_clarity', 'unknown')}")
    st.write(f"Conflict Visible: {feature_summary.get('conflict_visible', 'unknown')}")
    st.write(f"Payoff Teased: {feature_summary.get('payoff_teased', 'unknown')}")
    st.write(f"Curiosity Gap: {feature_summary.get('curiosity_gap', 'unknown')}")


def render_intro_observation(intro_observation):
    if intro_observation.get("status") != "success":
        st.write(
            "Intro observation is not available yet. Stratify used visual evidence instead."
        )
        return

    observations = intro_observation.get("observations", {})
    st.write(
        f"Opening Summary: {observations.get('opening_summary', 'unknown') or 'unknown'}"
    )
    st.write(f"Hook Type: {observations.get('hook_type', 'unknown') or 'unknown'}")
    st.write(
        f"Main Subject: {observations.get('main_subject', 'unknown') or 'unknown'}"
    )
    st.write(
        "Central Conflict: "
        f"{observations.get('central_conflict', 'unknown') or 'unknown'}"
    )
    st.write(
        f"Viewer Question: {observations.get('viewer_question', 'unknown') or 'unknown'}"
    )
    st.write(
        f"Story Promise: {observations.get('story_promise', 'unknown') or 'unknown'}"
    )
    st.write(
        f"Emotional Tone: {observations.get('emotional_tone', 'unknown') or 'unknown'}"
    )
    st.write(
        "First-Time Viewer Reaction: "
        f"{observations.get('first_time_viewer_reaction', 'unknown') or 'unknown'}"
    )
    st.write(
        "What Might Be Confusing: "
        f"{observations.get('what_might_be_confusing', 'unknown') or 'unknown'}"
    )
    st.write(
        f"First Impression: {observations.get('first_impression', 'unknown') or 'unknown'}"
    )
    st.write(f"Confidence: {intro_observation.get('confidence', 'low').title()}")
    st.write(f"Provider: {intro_observation.get('provider', 'unknown') or 'unknown'}")


def render_next_best_test(patterns):
    recommendation = strongest_recommendation(patterns)

    st.header("Your Next Best Test")
    if not recommendation:
        render_empty("No evidence-backed test met the current threshold yet.")
        return

    st.subheader(recommendation.get("title", "Evidence-based test"))
    st.write(first_sentence(recommendation.get("why_it_matters", "")))
    st.write(
        f"**Suggested test:** "
        f"{recommendation.get('suggested_test', 'No suggested test available.')}"
    )
    st.caption(f"Confidence: {recommendation.get('confidence', 'low').title()}")


def render_what_successful_videos_did(patterns):
    st.header("What Successful Videos Did Differently")
    opportunities = patterns.get("strongest_opportunities", [])
    if not opportunities:
        render_empty(
            "Stratify did not find a clear difference between stronger and weaker benchmark intros yet."
        )
        return

    for item in opportunities[:4]:
        label = item.get("label", "pattern").title()
        top_value = item.get("top_dominant_value", "unknown")
        user_value = item.get("user_value", "unknown")
        st.write(
            f"- **{label}:** stronger benchmark intros tended toward "
            f"'{top_value}'. Your intro was '{user_value}'."
        )


def render_feature_rows(feature_comparison):
    if not feature_comparison:
        render_empty()
        return

    for item in feature_comparison:
        st.write(f"**{item.get('label', 'Feature').title()}**")
        st.write(f"User intro: {item.get('user_value', 'unknown')}")
        st.write(item.get("top_evidence", "Top benchmarks: no evidence available."))
        st.write(
            item.get("lower_evidence", "Lower benchmarks: no evidence available.")
        )
        st.write(f"Position: {human_status(item.get('status'))}")
        st.caption(item.get("explanation", "No comparison explanation available."))


def render_position(items):
    if not items:
        render_empty("Stratify could not confidently position this intro yet.")
        return
    for item in items:
        st.write(f"- {item}")


def render_builder_signals(items, empty_message):
    if not items:
        render_empty(empty_message)
        return

    for item in items:
        st.write(f"**{item.get('label', 'Feature').title()}**")
        st.write(f"User intro: {item.get('user_value', 'unknown')}")
        st.write(
            f"Dominant top benchmark value: "
            f"{item.get('top_dominant_value', 'unknown')}"
        )
        st.write(
            f"Dominant lower benchmark value: "
            f"{item.get('lower_dominant_value', 'unknown')}"
        )
        st.caption(item.get("explanation", "No comparison explanation available."))


def render_builder_recommendations(items):
    if not items:
        render_empty("No recommendation met the current evidence threshold.")
        return

    for item in items:
        st.subheader(item.get("title", "Evidence-based test"))
        st.write(f"**Evidence:** {item.get('evidence', 'No evidence available.')}")
        st.write(item.get("why_it_matters", ""))
        st.write(f"**Suggested test:** {item.get('suggested_test', '')}")
        st.caption(f"Confidence: {item.get('confidence', 'low').title()}")


def render_creator_recommendations(items):
    if not items:
        render_empty("No evidence-backed test met the current threshold yet.")
        return

    for item in items:
        st.subheader(item.get("title", "Evidence-based test"))
        st.write(first_sentence(item.get("why_it_matters", "")))
        st.write(f"**Suggested test:** {item.get('suggested_test', '')}")
        st.caption(f"Confidence: {item.get('confidence', 'low').title()}")


def render_creator_alignment(comparisons):
    aligned = [
        item
        for item in comparisons
        if item.get("actionable") and item.get("status") == "aligned_with_top"
    ]
    if not aligned:
        render_empty("No discriminative top-pattern alignment could be confirmed.")
        return

    for item in aligned:
        st.write(f"**{item.get('label', 'Feature').title()}**")
        st.write(
            f"Your observed value '{item.get('user_value', 'unknown')}' matches the "
            "stronger benchmark pattern for this feature."
        )


def render_creator_holds(patterns):
    items = patterns.get("missing_winning_features", []) + patterns.get(
        "risk_signals", []
    )
    if not items:
        render_empty("No evidence-backed constraint was identified.")
        return

    for item in items:
        st.write(f"**{item.get('label', 'Feature').title()}**")
        st.write(
            f"Your intro was '{item.get('user_value', 'unknown')}'. The stronger "
            f"observed benchmark pattern was "
            f"'{item.get('top_dominant_value', 'unknown')}'."
        )


def render_creator_experiments(items):
    if not items:
        render_empty("No experiment met the current evidence threshold.")
        return

    for item in items:
        st.subheader(item.get("title", "Evidence-based experiment"))
        st.write(item.get("suggested_test", ""))
        st.caption(
            "Observed benchmark groups differed on this feature. "
            f"Confidence: {item.get('confidence', 'low').title()}."
        )



def render_reasoning_details(report):
    reasoning = report.get("reasoning", {})

    user_decisions = reasoning.get("user_decisions", {})
    decision_comparison = reasoning.get("decision_comparison", {})
    evidence_graph = reasoning.get("evidence_graph", {})

    st.subheader("Creator Decisions")
    decisions = user_decisions.get("decisions", [])

    if not decisions:
        render_empty("No creator decisions were inferred from the current evidence.")
    else:
        for decision in decisions[:5]:
            st.write(f"**{decision.get('decision_type', 'unknown')}**")
            st.write(decision.get("explanation", "No explanation available."))
            st.caption(f"Confidence: {decision.get('confidence', 'unknown').title()}")

    st.subheader("Decision Comparison")
    st.write(decision_comparison.get("summary", "No decision comparison available."))

    stronger_only = decision_comparison.get("stronger_only_decisions", [])
    weaker_only = decision_comparison.get("weaker_only_decisions", [])

    if stronger_only:
        st.write("**Decisions more associated with stronger benchmark intros:**")
        for item in stronger_only[:5]:
            st.write(f"- {item}")

    if weaker_only:
        st.write("**Decisions more associated with lower benchmark intros:**")
        for item in weaker_only[:5]:
            st.write(f"- {item}")

    st.subheader("Evidence Graph")
    chains = evidence_graph.get("chains", [])

    if not chains:
        render_empty("No evidence chains were built yet.")
        return

    for chain in chains[:5]:
        st.write(f"**{chain.get('decision_type', 'unknown')}**")
        st.write(chain.get("decision_explanation", "No decision explanation available."))

        evidence_chain = chain.get("evidence_chain", {})
        observed_events = evidence_chain.get("observed_events", [])

        if observed_events:
            st.write("Supporting observed events:")
            for event in observed_events[:4]:
                st.write(
                    f"- {event.get('event_type', 'unknown')} "
                    f"at {event.get('timestamp', 'unknown')}s"
                )

        alignment = evidence_chain.get("benchmark_alignment", {})
        st.caption(
            "Benchmark alignment — "
            f"top count: {alignment.get('top_count', 0)}, "
            f"lower count: {alignment.get('lower_count', 0)}"
        )
        st.caption(f"Evidence confidence: {chain.get('confidence', 'unknown').title()}")

def render_builder_details(report):
    patterns = report.get("patterns", {})
    benchmark = report.get("benchmark", {})
    benchmark_features = report.get("benchmark_features", {})
    feature_summary = report.get("feature_report", {}).get("feature_summary", {})
    intro_observation = report.get("intro_observation", {})

    with st.expander("Builder Details"):
        st.subheader("Intro Feature Values")
        render_intro_values(feature_summary)
        st.subheader("Storytelling Values")
        render_storytelling_values(feature_summary)
        st.subheader("Intro Observation")
        render_intro_observation(intro_observation)
        st.subheader("Benchmark Discovery")
        st.write(
            f"Relevant benchmark candidates: "
            f"{benchmark.get('candidate_count', len(benchmark.get('all_candidates', [])))}"
        )
        st.write(
            "Top performer intros analyzed: "
            f"{count_analyzed_intros(benchmark_features.get('top_performers', []))}"
        )
        st.write(
            "Lower performer intros analyzed: "
            f"{count_analyzed_intros(benchmark_features.get('lower_performers', []))}"
        )
        st.subheader("Evidence Details")
        render_feature_rows(patterns.get("feature_comparison", []))
        st.subheader("Reasoning Details")
        render_reasoning_details(report)
        st.subheader("Raw Backend Evidence")
        st.write(
            {
                "engines": {
                    "intro": INTRO_ENGINE,
                    "pattern": PATTERN_ENGINE,
                    "benchmark": BENCHMARK_ENGINE,
                    "recommendation": RECOMMENDATION_ENGINE,
                },
                "report": report,
            }
        )


def render_confidence(patterns):
    st.write(f"Confidence: {patterns.get('confidence', 'low').title()}")
    st.write(
        patterns.get(
            "confidence_reason",
            "Not enough benchmark intro evidence was available.",
        )
    )


def render_builder_report(report):
    category = report.get("category", {})
    benchmark = report.get("benchmark", {})
    benchmark_features = report.get("benchmark_features", {})
    patterns = report.get("patterns", {})
    feature_summary = report.get("feature_report", {}).get("feature_summary", {})
    intro_observation = report.get("intro_observation", {})

    render_next_best_test(patterns)
    st.divider()

    st.header("Benchmark Discovery")
    st.subheader("Detected Search Context")
    st.write(category.get("search_query", "No search context detected yet."))

    search_queries = category.get("search_queries", [])
    if search_queries:
        st.subheader("Search Queries")
        for query in search_queries:
            st.write(f"- {query}")

    st.subheader("Top Performers Found")
    top_performers = benchmark.get("top_performers", [])
    if top_performers:
        for video_item in top_performers:
            st.write(
                f"- {video_item.get('title')} "
                f"({video_item.get('views', 0):,} views)"
            )
    else:
        render_empty("No relevant top performers found.")

    st.subheader("Lower Performers Found")
    lower_performers = benchmark.get("lower_performers", [])
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
        f"Relevant benchmark candidates: "
        f"{benchmark.get('candidate_count', len(benchmark.get('all_candidates', [])))}"
    )
    st.caption(
        benchmark.get(
            "lower_performer_reason",
            "Lower-performer availability metadata was not provided.",
        )
    )
    st.write(
        "Top performer intros analyzed: "
        f"{count_analyzed_intros(benchmark_features.get('top_performers', []))}"
    )
    st.write(
        "Lower performer intros analyzed: "
        f"{count_analyzed_intros(benchmark_features.get('lower_performers', []))}"
    )
    st.divider()

    st.header("What Stratify Noticed")
    render_intro_observation(intro_observation)
    st.divider()

    render_what_successful_videos_did(patterns)
    st.divider()

    st.header("Opportunities")
    render_builder_signals(
        patterns.get("missing_winning_features", []),
        "No missing winning features were identified from the current evidence.",
    )
    st.divider()

    st.header("Patterns to Watch")
    render_builder_signals(
        patterns.get("risk_signals", []),
        "No risk signals were identified from the current evidence.",
    )
    st.divider()

    st.header("What To Test Next")
    render_creator_recommendations(patterns.get("top_creator_experiments", []))
    st.divider()

    with st.expander("Evidence Details"):
        render_feature_rows(patterns.get("feature_comparison", []))

    st.header("Final Verdict")
    st.write(
        patterns.get(
            "final_verdict",
            "Stratify does not have enough evidence to position this intro yet.",
        )
    )
    st.divider()

    st.header("Evidence Confidence")
    render_confidence(patterns)

    render_builder_details(report)


def render_creator_report(report):
    patterns = report.get("patterns", {})
    feature_summary = report.get("feature_report", {}).get("feature_summary", {})
    intro_observation = report.get("intro_observation", {})

    render_next_best_test(patterns)
    st.divider()

    st.header("What Stratify Noticed")
    render_intro_observation(intro_observation)
    st.divider()

    st.header("What You're Doing Well")
    render_creator_alignment(patterns.get("feature_comparison", []))
    st.divider()

    render_what_successful_videos_did(patterns)
    st.divider()

    st.header("Opportunities")
    render_builder_signals(
        patterns.get("missing_winning_features", []),
        "No opportunities were identified from the current evidence.",
    )
    st.divider()

    st.header("Patterns to Watch")
    render_builder_signals(
        patterns.get("risk_signals", []),
        "No patterns to watch were identified from the current evidence.",
    )
    st.divider()

    st.header("What To Test Next")
    render_creator_recommendations(patterns.get("top_creator_experiments", []))
    st.divider()

    with st.expander("Evidence Details"):
        render_feature_rows(patterns.get("feature_comparison", []))

    st.header("Final Verdict")
    st.write(
        patterns.get(
            "final_verdict",
            "Stratify does not have enough evidence to position this intro yet.",
        )
    )
    st.divider()

    st.header("Evidence Confidence")
    render_confidence(patterns)

    render_builder_details(report)


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

        if report.get("status") == "failed":
            status.update(
                label="Stratify could not build this report.",
                state="error",
                expanded=True,
            )
            warnings = report.get("warnings", [])
            for warning in warnings:
                st.error(warning)
            if has_youtube_download_block(warnings):
                st.info(YOUTUBE_BLOCK_FALLBACK)
            st.stop()

        status.update(
            label=(
                "Partial Stratify report ready."
                if report.get("status") == "partial"
                else "Stratify report ready."
            ),
            state="complete",
            expanded=False,
        )

    if report.get("warnings"):
        st.warning(
            "Stratify built the best available report, but some evidence was unavailable."
        )
        with st.expander("What happened?"):
            for warning in report["warnings"]:
                st.write(f"- {warning}")
            if has_youtube_download_block(report["warnings"]):
                st.info(YOUTUBE_BLOCK_FALLBACK)

    if ACTIVE_PRODUCT_MODE == "creator":
        render_creator_report(report)
    else:
        render_builder_report(report)