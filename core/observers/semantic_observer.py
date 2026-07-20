"""Deterministic semantic aggregation over raw intro frame observations."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping


VALID_FOCUS = {"person", "multiple_people", "object", "environment", "text", "mixed", "unavailable"}


@dataclass
class SemanticBeat:
    start_time: float
    end_time: float
    dominant_focus: str
    text_presence: bool
    composition_state: str
    transition_type: str
    semantic_description: str
    supporting_frames: List[int] = field(default_factory=list)
    confidence: str = "limited"


@dataclass
class SemanticObservation:
    version: str
    primary_visual_focus: str
    focus_clarity: str
    opening_mode: str
    visual_progression: str
    information_mode: str
    text_role: str
    subject_presence_pattern: str
    opening_clarity_summary: str
    semantic_confidence: str
    supporting_evidence: List[Dict[str, Any]]
    beats: List[SemanticBeat]
    unavailable_fields: List[str]
    metadata_context: Dict[str, Any]

    def to_dict(self):
        result = asdict(self)
        result["beats"] = [asdict(beat) for beat in self.beats]
        return result


def _number(frame, *keys):
    for key in keys:
        value = frame.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return max(int(value), 0)
    return 0


def _text(frame, key):
    value = frame.get(key)
    if isinstance(value, str) and value.strip().lower() not in {"", "unknown", "unavailable", "none"}:
        return value.strip().lower()
    return ""


def _focus(frame):
    explicit = _text(frame, "dominant_focus")
    if explicit in VALID_FOCUS:
        return explicit
    people = _number(frame, "subject_count", "person_count", "face_count")
    person = frame.get("human_presence") is True
    objects = _number(frame, "object_count") or int(frame.get("object_presence") is True)
    text = frame.get("text_overlay") is True
    scene = _text(frame, "scene_type")
    if people >= 2:
        return "multiple_people"
    if person and (objects or (text and scene not in {"person_with_text", "person"})):
        return "mixed"
    if person or scene in {"person", "person_with_text"}:
        return "person"
    if objects:
        return "object"
    if text and scene in {"text", "text_led"}:
        return "text"
    if scene and scene not in {"unknown", "person", "person_with_text", "text", "text_led"}:
        return "environment"
    if text:
        return "text"
    return "unavailable"


def _motion_state(frame):
    explicit = _text(frame, "motion_state") or _text(frame, "motion_level")
    if explicit:
        return explicit
    score = frame.get("motion_score")
    if isinstance(score, (int, float)):
        return "active" if score >= 18 else "moving" if score >= 7 else "held"
    energy = _text(frame, "visual_energy")
    return {"high": "active", "moderate": "moving", "low": "held"}.get(energy, "unavailable")


def _composition(frame):
    return _text(frame, "composition_state") or _text(frame, "composition") or _text(frame, "scene_type") or "unavailable"


def _signature(frame):
    return (_focus(frame), frame.get("text_overlay") is True, _composition(frame), _motion_state(frame))


def _beat_description(signature, previous=None):
    focus, text, composition, motion = signature
    if previous is None:
        if focus == "person" and text:
            return "The opening begins with one central figure while a written cue shares the frame."
        if focus == "person":
            return "The opening begins with one central figure as the main point of focus."
        if focus == "multiple_people":
            return "Several figures share the opening frame, so attention is divided from the start."
        if focus == "object":
            return "A single object leads the opening and establishes the first point of focus."
        if focus == "environment":
            return "The opening establishes the environment before introducing a singular subject."
        if focus == "text":
            return "A written message leads the opening before another visual subject becomes clear."
        return "The first composition does not establish a reliable dominant focus."
    old_focus, old_text, old_composition, old_motion = previous
    if focus != old_focus:
        if focus == "multiple_people":
            return "Additional figures enter the composition, making the frame less singular."
        if old_focus == "environment" and focus in {"person", "object"}:
            return "The sequence moves from context to a specific visual subject."
        return "A different visual element becomes dominant, creating a distinct new beat."
    if text != old_text:
        return "A written cue is introduced while the same visual subject remains in place." if text else "The written cue clears, leaving the visual subject to carry the frame."
    if composition != old_composition:
        return "The framing changes while the same subject remains the primary point of focus."
    if motion != old_motion:
        return "The amount of movement changes while the opening keeps the same central focus."
    return "The opening continues on the same setup without a meaningful compositional change."


def _group_beats(frames, confidence):
    if not frames:
        return []
    ordered = sorted(enumerate(frames), key=lambda item: float(item[1].get("timestamp", item[0]) or item[0]))
    groups = []
    for raw_index, frame in ordered:
        signature = _signature(frame)
        timestamp = float(frame.get("timestamp", raw_index) or raw_index)
        if groups and groups[-1]["signature"] == signature:
            groups[-1]["frames"].append(raw_index)
            groups[-1]["end"] = timestamp + 1.0
        else:
            groups.append({"signature": signature, "frames": [raw_index], "start": timestamp, "end": timestamp + 1.0})
    beats = []
    previous = None
    for group in groups:
        signature = group["signature"]
        beats.append(SemanticBeat(
            start_time=group["start"], end_time=group["end"], dominant_focus=signature[0],
            text_presence=signature[1], composition_state=signature[2],
            transition_type="opening" if previous is None else "meaningful_change",
            semantic_description=_beat_description(signature, previous),
            supporting_frames=group["frames"], confidence=confidence,
        ))
        previous = signature
    return beats


def _confidence(frames):
    if not frames:
        return "limited"
    usable = sum(_focus(frame) != "unavailable" or _composition(frame) != "unavailable" for frame in frames)
    coverage = usable / len(frames)
    if len(frames) >= 8 and coverage >= 0.75:
        return "high"
    if len(frames) >= 3 and coverage >= 0.5:
        return "moderate"
    return "limited"


def _opening_summary(primary, clarity, progression, information, text_role):
    if primary == "unavailable":
        return "The available frames do not establish a reliable visual focus, so the opening hierarchy remains unavailable."
    focus_phrase = {
        "person": "one central figure", "multiple_people": "several competing figures",
        "object": "one central object", "environment": "the surrounding environment",
        "text": "a written message", "mixed": "several visual elements",
    }[primary]
    clarity_phrase = {
        "immediate": "is clear from the first beat", "develops_early": "becomes clear within the early beats",
        "delayed": "does not become stable until later", "competing": "shares attention with competing elements",
        "unavailable": "cannot be timed reliably",
    }[clarity]
    progression_phrase = {
        "mostly_held": "The sequence largely holds one setup.",
        "gradual_change": "The setup develops through a small number of measured changes.",
        "frequent_change": "The sequence moves through several different compositions in quick succession.",
        "distinct_beats": "The sequence progresses through clearly separated visual beats.",
        "unavailable": "The progression cannot be classified reliably.",
    }[progression]
    text_phrase = ""
    if information == "image_and_text":
        text_phrase = " Written cues share attention with the imagery."
    elif information == "text_led":
        text_phrase = " Written information carries most of the opening context."
    elif text_role == "absent":
        text_phrase = " The imagery carries the opening without written context."
    return f"The opening is led by {focus_phrase}, which {clarity_phrase}. {progression_phrase}{text_phrase}"


def observe_semantics(frame_observations, metadata_context=None):
    frames = [dict(frame) for frame in frame_observations or [] if isinstance(frame, Mapping)]
    confidence = _confidence(frames)
    beats = _group_beats(frames, confidence)
    focuses = [_focus(frame) for frame in frames]
    available_focuses = [focus for focus in focuses if focus != "unavailable"]
    if not available_focuses:
        primary = "unavailable"
    elif "multiple_people" in available_focuses or len(set(available_focuses[:3])) >= 3:
        primary = "multiple_people" if "multiple_people" in available_focuses else "mixed"
    else:
        primary = max(set(available_focuses), key=lambda value: (available_focuses.count(value), -available_focuses.index(value)))

    early = available_focuses[:3]
    if not early:
        clarity = "unavailable"
    elif primary in {"multiple_people", "mixed"}:
        clarity = "competing"
    elif focuses and focuses[0] == primary:
        clarity = "competing" if len(early) >= 3 and early[0] == early[2] and early[1] != primary else "immediate"
    elif primary in focuses[:3]:
        clarity = "develops_early"
    else:
        clarity = "delayed"

    text_flags = [frame.get("text_overlay") is True for frame in frames]
    text_count = sum(text_flags)
    if not frames:
        text_role = "unavailable"
    elif text_count == 0:
        text_role = "absent"
    elif text_count == len(frames):
        text_role = "persistent"
    elif text_count / len(frames) >= 0.6:
        text_role = "dominant"
    else:
        text_role = "intermittent"

    image_count = sum(focus not in {"text", "unavailable"} for focus in focuses)
    information = "unavailable" if not frames else "text_led" if text_count and not image_count else "image_and_text" if text_count and image_count else "image_led" if image_count else "unavailable"
    first_focus = focuses[0] if focuses else "unavailable"
    opening_mode = {
        "person": "subject_first", "multiple_people": "subject_first", "object": "subject_first",
        "text": "text_first", "environment": "environment_first", "mixed": "mixed",
        "unavailable": "unavailable",
    }[first_focus]
    if first_focus == "unavailable" and frames and _motion_state(frames[0]) in {"active", "moving"}:
        opening_mode = "action_or_change_first"

    beat_count = len(beats)
    change_ratio = beat_count / len(frames) if frames else 0.0
    progression = (
        "unavailable" if not frames else
        "mostly_held" if beat_count == 1 else
        "gradual_change" if beat_count == 2 else
        "frequent_change" if beat_count >= 4 and change_ratio >= 0.75 else
        "distinct_beats"
    )
    person_flags = [focus in {"person", "multiple_people"} for focus in focuses]
    if not frames or not any(person_flags):
        subject_pattern = "unavailable"
    elif "multiple_people" in focuses:
        subject_pattern = "multiple_subjects"
    elif person_flags[0] and sum(person_flags) >= max(1, len(frames) // 2):
        subject_pattern = "present_immediately"
    elif not person_flags[0] and any(person_flags[1:]):
        subject_pattern = "enters_later"
    else:
        subject_pattern = "inconsistent"

    evidence = [{"frame_index": index, "timestamp": float(frame.get("timestamp", index) or index), "focus": focuses[index], "text_present": text_flags[index], "composition": _composition(frame), "motion_state": _motion_state(frame)} for index, frame in enumerate(frames)]
    unavailable = [name for name, value in (("primary_visual_focus", primary), ("focus_clarity", clarity), ("opening_mode", opening_mode), ("visual_progression", progression), ("information_mode", information), ("text_role", text_role), ("subject_presence_pattern", subject_pattern)) if value == "unavailable"]
    return SemanticObservation(
        version="observation-semantics-v2", primary_visual_focus=primary, focus_clarity=clarity,
        opening_mode=opening_mode, visual_progression=progression, information_mode=information,
        text_role=text_role, subject_presence_pattern=subject_pattern,
        opening_clarity_summary=_opening_summary(primary, clarity, progression, information, text_role),
        semantic_confidence=confidence, supporting_evidence=evidence, beats=beats,
        unavailable_fields=unavailable, metadata_context=dict(metadata_context or {}),
    ).to_dict()
