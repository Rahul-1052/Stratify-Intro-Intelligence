from typing import Any, Dict, List


def understand_temporal_flow(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Converts canonical intro events into temporal flow understanding.

    This module does not recommend or score.
    It explains how the intro evolves over time.
    """

    sorted_events = sorted(
        events or [],
        key=lambda item: float(item.get("timestamp", 0.0)),
    )

    if not sorted_events:
        return {
            "status": "unavailable",
            "phases": [],
            "summary": "No canonical events were available for temporal understanding.",
        }

    phases = _build_temporal_phases(sorted_events)

    return {
        "status": "success",
        "event_count": len(sorted_events),
        "phases": phases,
        "summary": _summarize_temporal_flow(sorted_events, phases),
    }


def _build_temporal_phases(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    early = [event for event in events if float(event.get("timestamp", 0.0)) <= 3]
    middle = [event for event in events if 3 < float(event.get("timestamp", 0.0)) <= 8]
    late = [event for event in events if float(event.get("timestamp", 0.0)) > 8]

    return [
        _phase("opening", "0–3s", early),
        _phase("development", "3–8s", middle),
        _phase("continuation_setup", "8s+", late),
    ]


def _phase(name: str, window: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "phase": name,
        "time_window": window,
        "events": events,
        "event_count": len(events),
        "description": _describe_phase(name, events),
    }


def _describe_phase(name: str, events: List[Dict[str, Any]]) -> str:
    if not events:
        return f"No major observable events were detected during the {name} phase."

    event_types = [event.get("event_type", "unknown") for event in events]

    return (
        f"The {name} phase contains {len(events)} observable events: "
        f"{', '.join(event_types)}."
    )


def _summarize_temporal_flow(
    events: List[Dict[str, Any]],
    phases: List[Dict[str, Any]],
) -> str:
    active_phases = [
        phase["phase"]
        for phase in phases
        if phase.get("event_count", 0) > 0
    ]

    return (
        f"The intro contains {len(events)} canonical events across "
        f"{len(active_phases)} active temporal phases: "
        f"{', '.join(active_phases)}."
    )