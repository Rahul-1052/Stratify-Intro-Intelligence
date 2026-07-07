from typing import Any, Dict, List


def understand_temporal_flow(frame_observations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Converts frame-level observations into temporal intro events.

    This module does not recommend or score.
    It only explains how the first seconds evolve over time.
    """

    observations = sorted(
        frame_observations or [],
        key=lambda item: float(item.get("timestamp", 0.0)),
    )

    if not observations:
        return {
            "status": "unavailable",
            "events": [],
            "summary": "No frame observations were available for temporal understanding.",
        }

    events = []

    previous = None

    for current in observations:
        if previous is None:
            events.append(_opening_event(current))
        else:
            events.extend(_change_events(previous, current))

        previous = current

    return {
        "status": "success",
        "events": events,
        "event_count": len(events),
        "summary": _summarize_events(events),
    }


def _opening_event(frame: Dict[str, Any]) -> Dict[str, Any]:
    timestamp = float(frame.get("timestamp", 0.0))

    return {
        "timestamp": timestamp,
        "event_type": "intro_start",
        "description": _describe_opening(frame),
        "evidence": frame,
    }


def _describe_opening(frame: Dict[str, Any]) -> str:
    subject = (
        "a visible human subject"
        if frame.get("human_presence")
        else "no clearly visible human subject"
    )

    text = (
        "with visible text or graphic overlay"
        if frame.get("text_overlay")
        else "without visible text or graphic overlay"
    )

    lighting = frame.get("dominant_lighting", "unknown")
    energy = frame.get("visual_energy", "unknown")
    scene = frame.get("scene_type", "unknown")

    return (
        f"The intro begins with {subject}, {text}, "
        f"{lighting} lighting, {energy} visual energy, "
        f"and a {scene} scene structure."
    )


def _change_events(
    previous: Dict[str, Any],
    current: Dict[str, Any],
) -> List[Dict[str, Any]]:
    events = []
    timestamp = float(current.get("timestamp", 0.0))

    if previous.get("human_presence") is False and current.get("human_presence") is True:
        events.append({
            "timestamp": timestamp,
            "event_type": "subject_appears",
            "description": "A human subject becomes visible after not being clearly present.",
            "evidence": current,
        })

    if previous.get("human_presence") is True and current.get("human_presence") is False:
        events.append({
            "timestamp": timestamp,
            "event_type": "subject_disappears",
            "description": "The visible human subject is no longer clearly present.",
            "evidence": current,
        })

    if previous.get("text_overlay") is False and current.get("text_overlay") is True:
        events.append({
            "timestamp": timestamp,
            "event_type": "text_appears",
            "description": "Text or graphic overlay appears in the intro.",
            "evidence": current,
        })

    if previous.get("text_overlay") is True and current.get("text_overlay") is False:
        events.append({
            "timestamp": timestamp,
            "event_type": "text_disappears",
            "description": "Text or graphic overlay disappears from the intro.",
            "evidence": current,
        })

    if previous.get("visual_energy") != current.get("visual_energy"):
        events.append({
            "timestamp": timestamp,
            "event_type": "energy_shift",
            "description": (
                f"Visual energy changes from {previous.get('visual_energy')} "
                f"to {current.get('visual_energy')}."
            ),
            "evidence": current,
        })

    if previous.get("scene_type") != current.get("scene_type"):
        events.append({
            "timestamp": timestamp,
            "event_type": "scene_shift",
            "description": (
                f"Scene structure changes from {previous.get('scene_type')} "
                f"to {current.get('scene_type')}."
            ),
            "evidence": current,
        })

    return events


def _summarize_events(events: List[Dict[str, Any]]) -> str:
    if not events:
        return "No meaningful temporal events were detected."

    event_types = [event.get("event_type", "unknown") for event in events]

    return (
        f"Detected {len(events)} temporal events in the intro, including "
        f"{', '.join(event_types[:6])}."
    )