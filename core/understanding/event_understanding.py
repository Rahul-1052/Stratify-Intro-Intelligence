from typing import Any, Dict, List


def understand_intro_events(frame_observations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Converts low-level frame observations into canonical intro events.

    This module does not recommend, score, or compare.
    It creates stable events that future Stratify modules can reason over.
    """

    observations = sorted(
        frame_observations or [],
        key=lambda item: float(item.get("timestamp", 0.0)),
    )

    if not observations:
        return {
            "status": "unavailable",
            "events": [],
            "event_count": 0,
            "summary": "No frame observations were available for event understanding.",
        }

    events = []
    previous = None

    for current in observations:
        if previous is None:
            events.append(_intro_start_event(current))
        else:
            events.extend(_detect_event_changes(previous, current))

        previous = current

    return {
        "status": "success",
        "events": events,
        "event_count": len(events),
        "summary": _summarize_events(events),
    }


def _intro_start_event(frame: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "timestamp": float(frame.get("timestamp", 0.0)),
        "event_type": "intro_start",
        "description": _describe_intro_start(frame),
        "evidence": frame,
    }


def _detect_event_changes(
    previous: Dict[str, Any],
    current: Dict[str, Any],
) -> List[Dict[str, Any]]:
    events = []
    timestamp = float(current.get("timestamp", 0.0))

    if previous.get("human_presence") is False and current.get("human_presence") is True:
        events.append(_event(
            timestamp,
            "subject_appears",
            "A human subject becomes visible after not being clearly present.",
            current,
        ))

    if previous.get("human_presence") is True and current.get("human_presence") is False:
        events.append(_event(
            timestamp,
            "subject_disappears",
            "The visible human subject is no longer clearly present.",
            current,
        ))

    if previous.get("text_overlay") is False and current.get("text_overlay") is True:
        events.append(_event(
            timestamp,
            "text_appears",
            "Text or graphic overlay appears in the intro.",
            current,
        ))

    if previous.get("text_overlay") is True and current.get("text_overlay") is False:
        events.append(_event(
            timestamp,
            "text_disappears",
            "Text or graphic overlay disappears from the intro.",
            current,
        ))

    if previous.get("visual_energy") != current.get("visual_energy"):
        events.append(_event(
            timestamp,
            "energy_shift",
            (
                f"Visual energy changes from {previous.get('visual_energy')} "
                f"to {current.get('visual_energy')}."
            ),
            current,
        ))

    if previous.get("scene_type") != current.get("scene_type"):
        events.append(_event(
            timestamp,
            "scene_shift",
            (
                f"Scene structure changes from {previous.get('scene_type')} "
                f"to {current.get('scene_type')}."
            ),
            current,
        ))

    if previous.get("dominant_lighting") != current.get("dominant_lighting"):
        events.append(_event(
            timestamp,
            "lighting_shift",
            (
                f"Lighting changes from {previous.get('dominant_lighting')} "
                f"to {current.get('dominant_lighting')}."
            ),
            current,
        ))

    return events


def _event(
    timestamp: float,
    event_type: str,
    description: str,
    evidence: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "timestamp": timestamp,
        "event_type": event_type,
        "description": description,
        "evidence": evidence,
    }


def _describe_intro_start(frame: Dict[str, Any]) -> str:
    subject = (
        "a visible human subject"
        if frame.get("human_presence")
        else "no clearly visible human subject"
    )

    text = (
        "visible text or graphic overlay"
        if frame.get("text_overlay")
        else "no visible text or graphic overlay"
    )

    return (
        f"The intro starts with {subject}, {text}, "
        f"{frame.get('dominant_lighting', 'unknown')} lighting, "
        f"{frame.get('visual_energy', 'unknown')} energy, "
        f"and a {frame.get('scene_type', 'unknown')} scene structure."
    )


def _summarize_events(events: List[Dict[str, Any]]) -> str:
    if not events:
        return "No canonical intro events were detected."

    event_types = [event.get("event_type", "unknown") for event in events]

    return (
        f"Detected {len(events)} canonical intro events, including "
        f"{', '.join(event_types[:6])}."
    )