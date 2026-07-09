from typing import Any, Dict, List


def build_evidence_graph(
    intro_understanding: Dict[str, Any],
    user_decisions: Dict[str, Any],
    benchmark_decisions: Dict[str, Any],
    decision_comparison: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Builds traceable evidence chains from observations to decisions.

    This module does not recommend.
    This module does not score.
    It only connects evidence across the reasoning pipeline.
    """

    events = intro_understanding.get("events", {}).get("events", [])
    temporal = intro_understanding.get("temporal", {})
    narrative = intro_understanding.get("narrative_draft", {})
    decisions = user_decisions.get("decisions", [])

    chains = []

    for decision in decisions:
        chains.append(
            _build_decision_chain(
                decision=decision,
                events=events,
                temporal=temporal,
                narrative=narrative,
                decision_comparison=decision_comparison,
            )
        )

    return {
        "status": "success" if chains else "limited",
        "chains": chains,
        "chain_count": len(chains),
        "summary": _summarize_graph(chains),
    }


def _build_decision_chain(
    decision: Dict[str, Any],
    events: List[Dict[str, Any]],
    temporal: Dict[str, Any],
    narrative: Dict[str, Any],
    decision_comparison: Dict[str, Any],
) -> Dict[str, Any]:
    decision_type = decision.get("decision_type", "unknown")

    supporting_events = _supporting_events_for_decision(
        decision_type=decision_type,
        events=events,
    )

    benchmark_alignment = _benchmark_alignment(
        decision_type=decision_type,
        decision_comparison=decision_comparison,
    )

    return {
        "decision_type": decision_type,
        "decision_explanation": decision.get("explanation", ""),
        "evidence_chain": {
            "observed_events": supporting_events,
            "temporal_context": _temporal_context(temporal),
            "narrative_context": _narrative_context(narrative),
            "benchmark_alignment": benchmark_alignment,
        },
        "confidence": _chain_confidence(
            supporting_events=supporting_events,
            benchmark_alignment=benchmark_alignment,
        ),
    }


def _supporting_events_for_decision(
    decision_type: str,
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    event_map = {
        "open_with_momentum": {"pace_accelerates", "visual_focus_shifts"},
        "delay_subject_reveal": {"subject_enters"},
        "add_context_with_visual_text": {"text_or_graphic_appears"},
        "shift_visual_attention": {"visual_focus_shifts", "scene_structure_changes"},
        "structure_intro_in_phases": {
            "opening_established",
            "pace_accelerates",
            "pace_slows",
            "visual_focus_shifts",
            "scene_structure_changes",
        },
        "establish_opening_goal": {
            "opening_established",
            "subject_enters",
            "text_or_graphic_appears",
            "visual_focus_shifts",
        },
    }

    allowed_events = event_map.get(decision_type, set())

    if not allowed_events:
        return []

    return [
        event
        for event in events
        if event.get("event_type") in allowed_events
    ]


def _benchmark_alignment(
    decision_type: str,
    decision_comparison: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "matches_top_benchmarks": decision_type in decision_comparison.get(
            "matching_top_decisions", []
        ),
        "matches_lower_benchmarks": decision_type in decision_comparison.get(
            "matching_lower_decisions", []
        ),
        "missing_from_user_but_seen_in_top": decision_type in decision_comparison.get(
            "missing_top_decisions", []
        ),
        "associated_with_stronger_benchmarks": decision_type in decision_comparison.get(
            "stronger_only_decisions", []
        ),
        "associated_with_lower_benchmarks": decision_type in decision_comparison.get(
            "weaker_only_decisions", []
        ),
        "top_count": decision_comparison.get("top_decision_counts", {}).get(
            decision_type, 0
        ),
        "lower_count": decision_comparison.get("lower_decision_counts", {}).get(
            decision_type, 0
        ),
    }


def _temporal_context(temporal: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "summary": temporal.get("summary", ""),
        "phases": temporal.get("phases", []),
        "event_count": temporal.get("event_count", 0),
    }


def _narrative_context(narrative: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "confidence": narrative.get("confidence", "unknown"),
        "opening_goal": narrative.get("opening_goal", ""),
        "viewer_expectation": narrative.get("viewer_expectation", ""),
        "story_promise": narrative.get("story_promise", ""),
        "unanswered_question": narrative.get("unanswered_question", ""),
    }


def _chain_confidence(
    supporting_events: List[Dict[str, Any]],
    benchmark_alignment: Dict[str, Any],
) -> str:
    event_count = len(supporting_events)
    top_count = benchmark_alignment.get("top_count", 0)
    lower_count = benchmark_alignment.get("lower_count", 0)

    if event_count >= 2 and top_count >= 2 and top_count > lower_count:
        return "moderate"

    if event_count >= 1 and top_count >= 1:
        return "limited"

    if event_count >= 1:
        return "low"

    return "unknown"


def _summarize_graph(chains: List[Dict[str, Any]]) -> str:
    if not chains:
        return "No evidence chains were built from the current reasoning outputs."

    decision_types = [
        chain.get("decision_type", "unknown")
        for chain in chains
    ]

    return (
        f"Built {len(chains)} evidence chain(s) connecting observations, "
        f"creator decisions, and benchmark alignment: "
        f"{', '.join(decision_types[:5])}."
    )