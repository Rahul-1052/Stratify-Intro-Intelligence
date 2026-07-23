import streamlit as st

from ui.components import clean_value
from ui.evaluation import render_evaluation_dashboard


def _empty(message="No evidence available yet."):
    st.caption(message)


def _count_analyzed_intros(items):
    return sum(
        bool(item.get("features", {}).get("feature_summary", {}))
        for item in items or []
        if isinstance(item, dict)
    )


def _render_video_list(items, empty_message):
    if not items:
        _empty(empty_message)
        return
    for item in items:
        title = item.get("title", "Untitled video")
        views = item.get("views")
        suffix = f" · {views:,} views" if isinstance(views, (int, float)) else ""
        st.markdown(f"- {title}{suffix}")


def _render_intro_details(report, show_creative_understanding=False):
    features = report.get("feature_report", {}).get("feature_summary", {}) or {}
    intro = report.get("intro_observation", {}) or {}
    observation = intro.get("observation") or intro.get("observations") or {}

    st.subheader("Observed intro details")
    feature_labels = (
        ("Frames analyzed", "frames_analyzed"),
        ("Lighting", "dominant_lighting"),
        ("Color feel", "dominant_color_feel"),
        ("Motion", "motion_level"),
        ("Scene changes", "scene_change_count"),
        ("Pacing", "pacing_level"),
        ("Visual energy", "visual_energy"),
        ("Human presence", "human_presence"),
        ("Text overlay", "text_overlay"),
        ("Scene type", "scene_type"),
        ("First-frame strength", "first_frame_strength"),
        ("Opening action", "opening_action_type"),
        ("Hook in first three seconds", "hook_visible_in_first_3_seconds"),
        ("Subject clarity", "subject_clarity"),
        ("Conflict visible", "conflict_visible"),
        ("Payoff teased", "payoff_teased"),
        ("Curiosity gap", "curiosity_gap"),
    )
    visible = {label: features.get(key) for label, key in feature_labels if clean_value(features.get(key))}
    if visible:
        st.write(visible)
    else:
        _empty("No structured visual features were available.")

    if isinstance(observation, dict) and observation:
        st.caption(
            f"Observation confidence: {clean_value(observation.get('confidence') or intro.get('confidence')) or 'unavailable'}"
        )
        st.write(observation)
    else:
        _empty("No structured intro observation was available.")

    semantic = report.get("semantic_observation", {}) or {}
    st.subheader("Semantic Observation V2")
    if semantic:
        st.caption("Opening-level aggregation")
        st.write({
            key: semantic.get(key)
            for key in (
                "version", "primary_visual_focus", "focus_clarity", "opening_mode",
                "visual_progression", "information_mode", "text_role",
                "subject_presence_pattern", "semantic_confidence", "unavailable_fields",
            )
        })
        st.caption("Semantic beat boundaries and supporting timestamps")
        st.write(semantic.get("beats", []))
        st.caption("Temporal calibration diagnostics")
        st.write(semantic.get("temporal_diagnostics", {}))
        st.caption("Direct visual evidence")
        st.write(semantic.get("supporting_evidence", []))
        st.caption("Metadata context — not treated as visual evidence")
        st.write(semantic.get("metadata_context", {}))
    else:
        _empty("No semantic aggregation was available.")

    if show_creative_understanding:
        st.subheader("Temporal Evidence V2")
        st.caption("Adaptive sampling plan, persistence windows, confidence reasons, and rejected isolated detections")
        st.write({"sampling": report.get("sampling", {}), "temporal_evidence": report.get("temporal_evidence", {})})

        st.subheader("Creative Structure")
        structure = report.get("creative_structure", {}) or {}
        if structure:
            st.caption("Deterministic organization derived only from Semantic Observation")
            st.write(structure)
        else:
            _empty("No creative structure was available.")

        st.subheader("Creative Understanding")
        creative_understanding = report.get("creative_understanding", {}) or {}
        if creative_understanding:
            st.caption("Recommendation-free interpretation of the opening's organization")
            st.write(creative_understanding)
        else:
            _empty("No creative understanding was available.")


def _render_benchmark_discovery(report):
    category = report.get("category", {}) or {}
    benchmark = report.get("benchmark", {}) or {}
    benchmark_features = report.get("benchmark_features", {}) or {}

    st.subheader("Benchmark Discovery")
    search_query = clean_value(category.get("search_query"))
    if search_query:
        st.caption("Detected search context")
        st.write(search_query)

    queries = category.get("search_queries", []) or []
    st.caption("Search queries")
    if queries:
        for query in queries:
            st.markdown(f"- {query}")
    else:
        _empty("No search queries were generated.")

    st.caption("Stronger comparison videos")
    _render_video_list(
        benchmark.get("top_performers", []), "No reliable stronger set was formed."
    )
    st.caption("Lower comparison videos")
    _render_video_list(
        benchmark.get("lower_performers", []), "No reliable lower set was formed."
    )

    st.write(
        {
            "candidate_count": benchmark.get(
                "candidate_count", len(benchmark.get("all_candidates", []))
            ),
            "stronger_intros_analyzed": _count_analyzed_intros(
                benchmark_features.get("top_performers", [])
            ),
            "lower_intros_analyzed": _count_analyzed_intros(
                benchmark_features.get("lower_performers", [])
            ),
            "lower_performer_reason": benchmark.get("lower_performer_reason"),
        }
    )


def _render_qualification(report):
    qualification = report.get("benchmark", {}).get("qualification", {}) or {}
    st.subheader("Benchmark Qualification")
    st.write(
        {
            "status": qualification.get("status", "unavailable"),
            "reason": qualification.get("reason"),
            "observed_candidate_count": qualification.get(
                "observed_candidate_count", 0
            ),
            "qualified_candidate_count": qualification.get(
                "qualified_candidate_count", 0
            ),
        }
    )
    diagnostics = qualification.get("diagnostics", []) or []
    if not diagnostics:
        _empty("No candidate qualification diagnostics were recorded.")
        return
    for item in diagnostics:
        status = str(item.get("qualification_status", "unknown")).replace("_", " ")
        title = item.get("title", "Untitled candidate")
        with st.expander(f"{status.title()}: {title}", expanded=False):
            st.write(
                {
                    "evidence_mode": item.get("evidence_mode"),
                    "metadata_compatibility": item.get("metadata_compatibility"),
                    "observed_intro_compatibility": item.get(
                        "observed_intro_compatibility"
                    ),
                    "viewer_job_compatibility": item.get(
                        "viewer_job_compatibility"
                    ),
                    "evidence_coverage": item.get("evidence_coverage"),
                    "compatibility_confidence": item.get(
                        "compatibility_confidence"
                    ),
                    "rejection_reason": item.get("rejection_reason"),
                    "viewer_job_assessment": item.get(
                        "viewer_job_assessment", {}
                    ),
                    "performance": item.get("performance", {}),
                }
            )


def _render_evidence_details(report):
    comparisons = report.get("patterns", {}).get("feature_comparison", []) or []
    st.subheader("Evidence Details")
    if not comparisons:
        _empty("No feature-level comparison evidence was available.")
        return
    for item in comparisons:
        st.markdown(f"**{str(item.get('label', 'Feature')).title()}**")
        st.write(
            {
                "current": item.get("user_value"),
                "stronger": item.get("top_dominant_value"),
                "lower": item.get("lower_dominant_value"),
                "status": item.get("status"),
                "top_evidence": item.get("top_evidence"),
                "lower_evidence": item.get("lower_evidence"),
                "explanation": item.get("explanation"),
            }
        )


def _render_reasoning_details(report, show_creative_trace=False):
    reasoning = report.get("reasoning", {}) or {}
    user_decisions = reasoning.get("user_decisions", {}) or {}
    decision_comparison = reasoning.get("decision_comparison", {}) or {}
    evidence_graph = reasoning.get("evidence_graph", {}) or {}
    creative = reasoning.get("creative_reasoning", {}) or {}

    st.subheader("Reasoning Details")
    decisions = user_decisions.get("decisions", []) or []
    st.caption("Creator decisions")
    if decisions:
        for decision in decisions[:5]:
            st.markdown(f"**{decision.get('decision_type', 'Unknown')}**")
            st.write(decision.get("explanation", "No explanation available."))
            st.caption(f"Confidence: {decision.get('confidence', 'unknown')}")
    else:
        _empty("No creator decisions were inferred.")

    st.caption("Decision comparison")
    st.write(decision_comparison.get("summary", "No comparison available."))
    if decision_comparison.get("stronger_only_decisions"):
        st.write(
            {"stronger_only": decision_comparison.get("stronger_only_decisions")}
        )
    if decision_comparison.get("weaker_only_decisions"):
        st.write({"lower_only": decision_comparison.get("weaker_only_decisions")})

    st.caption("Evidence graph")
    chains = evidence_graph.get("chains", []) or []
    if chains:
        for chain in chains[:5]:
            st.write(chain)
    else:
        _empty("No evidence chains were built.")

    if show_creative_trace:
        st.caption("Creative reasoning traceability")
        trace = creative.get("traceability", {}) or {}
        if trace:
            st.write({
                "semantic_evidence": trace.get("semantic_evidence", []),
                "creative_structure": trace.get("creative_structure", {}),
                "creative_understanding": trace.get("creative_understanding", {}),
                "opportunity_candidates": trace.get("opportunity_candidates", []),
                "selected_opportunity": trace.get("selected_opportunity"),
                "experiments": trace.get("experiments", []),
                "compatibility_mode": trace.get("compatibility_mode", False),
            })
        else:
            _empty("No creative reasoning trace was available.")


def _render_acquisition(report):
    acquisition = report.get("acquisition", {}) or {}
    st.subheader("Acquisition")
    st.write(
        {
            "source": acquisition.get("source", "unknown"),
            "method": acquisition.get("method", "unknown"),
        }
    )
    attempts = acquisition.get("attempts", []) or []
    if attempts:
        st.caption("Acquisition attempts")
        st.write(attempts)


def render_advanced_analysis(report, product_mode, version_metadata):
    with st.expander("Advanced Analysis", expanded=False):
        st.caption(
            "Detailed discovery, qualification, reasoning, acquisition, and raw evidence."
        )
        _render_benchmark_discovery(report)
        st.divider()
        _render_qualification(report)
        st.divider()
        _render_intro_details(report, show_creative_understanding=product_mode == "builder")
        st.divider()
        _render_evidence_details(report)
        st.divider()
        _render_reasoning_details(report, show_creative_trace=product_mode == "builder")
        st.divider()
        _render_acquisition(report)
        st.divider()

        st.subheader("Engine and version metadata")
        st.write({"product_mode": product_mode, **version_metadata})

        st.subheader("Raw backend evidence")
        st.json(report, expanded=False)

    if product_mode == "builder":
        render_evaluation_dashboard()
