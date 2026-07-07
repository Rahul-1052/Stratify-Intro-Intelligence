from typing import Any, Dict, List


MIN_MOTION_SPIKE = 8.0
MIN_BRIGHTNESS_SHIFT = 25.0
MIN_CONTRAST_SHIFT = 18.0


def understand_intro_events(frame_observations: List[Dict[str, Any]]) -> Dict[str, Any]:
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

    events = [_intro_start_event(observations[0])]

    for previous, current in zip(observations, observations[1:]):
        events.extend(_detect_canonical_events(previous, current))

    events = _dedupe_nearby_events(events)

    return {
        "status": "success",
        "events": events,
        "event_count": len(events),
        "summary": _summarize_events(events),
    }


def _intro_start_event(frame: Dict[str, Any]) -> Dict[str, Any]:
    return _event(
        timestamp=float(frame.get("timestamp", 0.0)),
        event_type="opening_established",
        confidence=0.85,
        evidence=frame,
        signals={
            "human_presence": frame.get("human_presence"),
            "text_overlay": frame.get("text_overlay"),
            "visual_energy": frame.get("visual_energy"),
            "scene_type": frame.get("scene_type"),
        },
    )


def _detect_canonical_events(
    previous: Dict[str, Any],
    current: Dict[str, Any],
) -> List[Dict[str, Any]]:
    events = []
    timestamp = float(current.get("timestamp", 0.0))

    previous_motion = float(previous.get("motion_score", 0.0) or 0.0)
    current_motion = float(current.get("motion_score", 0.0) or 0.0)

    previous_brightness = float(previous.get("brightness_score", 0.0) or 0.0)
    current_brightness = float(current.get("brightness_score", 0.0) or 0.0)

    previous_contrast = float(previous.get("contrast_score", 0.0) or 0.0)
    current_contrast = float(current.get("contrast_score", 0.0) or 0.0)

    if previous.get("human_presence") is False and current.get("human_presence") is True:
        events.append(_event(
            timestamp,
            "subject_enters",
            0.8,
            current,
            {"change": "human_presence_false_to_true"},
        ))

    if previous.get("human_presence") is True and current.get("human_presence") is False:
        events.append(_event(
            timestamp,
            "subject_leaves_frame",
            0.7,
            current,
            {"change": "human_presence_true_to_false"},
        ))

    if previous.get("text_overlay") is False and current.get("text_overlay") is True:
        events.append(_event(
            timestamp,
            "text_or_graphic_appears",
            0.75,
            current,
            {"change": "text_overlay_false_to_true"},
        ))

    if previous.get("text_overlay") is True and current.get("text_overlay") is False:
        events.append(_event(
            timestamp,
            "text_or_graphic_clears",
            0.7,
            current,
            {"change": "text_overlay_true_to_false"},
        ))

    motion_delta = current_motion - previous_motion
    if motion_delta >= MIN_MOTION_SPIKE:
        events.append(_event(
            timestamp,
            "pace_accelerates",
            0.7,
            current,
            {
                "previous_motion_score": previous_motion,
                "current_motion_score": current_motion,
                "motion_delta": round(motion_delta, 2),
            },
        ))

    if motion_delta <= -MIN_MOTION_SPIKE:
        events.append(_event(
            timestamp,
            "pace_slows",
            0.65,
            current,
            {
                "previous_motion_score": previous_motion,
                "current_motion_score": current_motion,
                "motion_delta": round(motion_delta, 2),
            },
        ))

    brightness_delta = abs(current_brightness - previous_brightness)
    contrast_delta = abs(current_contrast - previous_contrast)

    if brightness_delta >= MIN_BRIGHTNESS_SHIFT or contrast_delta >= MIN_CONTRAST_SHIFT:
        events.append(_event(
            timestamp,
            "visual_focus_shifts",
            0.68,
            current,
            {
                "brightness_delta": round(brightness_delta, 2),
                "contrast_delta": round(contrast_delta, 2),
            },
        ))

    if previous.get("scene_type") != current.get("scene_type"):
        events.append(_event(
            timestamp,
            "scene_structure_changes",
            0.72,
            current,
            {
                "previous_scene_type": previous.get("scene_type"),
                "current_scene_type": current.get("scene_type"),
            },
        ))

    return events


def _event(
    timestamp: float,
    event_type: str,
    confidence: float,
    evidence: Dict[str, Any],
    signals: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "timestamp": timestamp,
        "event_type": event_type,
        "confidence": confidence,
        "evidence": evidence,
        "signals": signals,
    }


def _dedupe_nearby_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped = []
    seen = set()

    for event in events:
        event_type = event.get("event_type")
        timestamp_bucket = int(float(event.get("timestamp", 0.0)))

        key = (event_type, timestamp_bucket)

        if key in seen:
            continue

        seen.add(key)
        deduped.append(event)

    return deduped


def _summarize_events(events: List[Dict[str, Any]]) -> str:
    if not events:
        return "No canonical intro events were detected."

    event_types = [event.get("event_type", "unknown") for event in events]

    return (
        f"Detected {len(events)} canonical intro events: "
        f"{', '.join(event_types[:8])}."
    )