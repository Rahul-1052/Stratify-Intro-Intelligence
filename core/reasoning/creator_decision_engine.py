from typing import Any, Dict, List


def infer_creator_decisions(intro_understanding: Dict[str, Any]) -> Dict[str, Any]:
    """
    Infers creator decisions from observed intro events.

    This does not recommend.
    This does not compare benchmarks.
    It translates observations into likely creative choices.
    """

    events = intro_understanding.get("events", {}).get("events", [])
    temporal = intro_understanding.get("temporal", {})
    narrative = intro_understanding.get("narrative_draft", {})

    decisions = []

    decisions.extend(_decisions_from_events(events))
    decisions.extend(_decisions_from_temporal_flow(temporal))
    decisions.extend(_decisions_from_narrative_draft(narrative))

    return {
        "status": "success" if decisions else "limited",
        "decisions": decisions,
        "decision_count": len(decisions),
        "summary": _summarize_decisions(decisions),
    }


def _decisions_from_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    decisions = []

    event_types = [event.get("event_type") for event in events]

    if "pace_accelerates" in event_types:
        decisions.append(_decision(
            "open_with_momentum",
            "The creator appears to increase movement or visual intensity during the intro.",
            events,
        ))

    if "subject_enters" in event_types:
        decisions.append(_decision(
            "delay_subject_reveal",
            "The creator appears to introduce the visible subject after the intro has already started.",
            events,
        ))

    if "text_or_graphic_appears" in event_types:
        decisions.append(_decision(
            "add_context_with_visual_text",
            "The creator appears to use text or graphics to add context during the intro.",
            events,
        ))

    if "visual_focus_shifts" in event_types:
        decisions.append(_decision(
            "shift_visual_attention",
            "The creator appears to change visual focus to refresh viewer attention.",
            events,
        ))

    return decisions


def _decisions_from_temporal_flow(temporal: Dict[str, Any]) -> List[Dict[str, Any]]:
    phases = temporal.get("phases", [])

    active_phases = [
        phase.get("phase")
        for phase in phases
        if phase.get("event_count", 0) > 0
    ]

    if len(active_phases) >= 2:
        return [_decision(
            "structure_intro_in_phases",
            "The creator appears to structure the intro across multiple temporal phases.",
            phases,
        )]

    return []


def _decisions_from_narrative_draft(narrative: Dict[str, Any]) -> List[Dict[str, Any]]:
    if narrative.get("status") != "success":
        return []

    opening_goal = narrative.get("opening_goal", "")

    if opening_goal and "unclear" not in opening_goal.lower():
        return [_decision(
            "establish_opening_goal",
            opening_goal,
            narrative.get("evidence_used", {}),
        )]

    return []


def _decision(
    decision_type: str,
    explanation: str,
    evidence: Any,
) -> Dict[str, Any]:
    return {
        "decision_type": decision_type,
        "explanation": explanation,
        "evidence": evidence,
        "confidence": "limited",
    }


def _summarize_decisions(decisions: List[Dict[str, Any]]) -> str:
    if not decisions:
        return "No creator decisions were inferred from the current intro evidence."

    decision_types = [decision.get("decision_type", "unknown") for decision in decisions]

    return (
        f"Inferred {len(decisions)} possible creator decision(s): "
        f"{', '.join(decision_types[:5])}."
    )