"""Deterministic temporal calibration over raw intro frame observations."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping


VALID_FOCUS = {
    "person", "multiple_people", "alternating_subjects", "object",
    "environment", "text", "mixed", "unavailable",
}


@dataclass(frozen=True)
class BeatCalibrationConfig:
    """Documented persistence rules for semantic boundary decisions."""

    minimum_persistent_samples: int = 2
    brief_interruption_samples: int = 1
    alternating_min_states: int = 3
    frequent_change_ratio: float = 0.75
    frequent_change_min_beats: int = 4


DEFAULT_CALIBRATION = BeatCalibrationConfig()


@dataclass
class SemanticBeat:
    start_time: float
    end_time: float
    dominant_focus: str
    text_presence: bool
    composition_state: str
    transition_type: str
    beat_purpose: str
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
    temporal_diagnostics: Dict[str, Any]
    text_evidence_confidence: str = "limited"

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
    if person and (objects or (text and scene not in {"person_with_text", "person", "person_focused"})):
        return "mixed"
    if person or scene in {"person", "person_with_text", "person_focused"}:
        return "person"
    if objects:
        return "object"
    if text and scene in {"text", "text_led", "text_or_graphic_focused"}:
        return "text"
    if scene and scene not in {"unknown", "person", "person_with_text", "person_focused", "text", "text_led", "text_or_graphic_focused"}:
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


def _environment(frame):
    return _text(frame, "environment") or _text(frame, "location") or _text(frame, "setting") or _text(frame, "scene_group") or "unavailable"


def _purpose(focus, text_present, motion):
    if focus == "environment":
        return "environment_setup"
    if focus == "multiple_people" or focus == "alternating_subjects":
        return "multi_subject_sequence"
    if focus == "text":
        return "text_led_context"
    if focus == "person":
        return "subject_establishment"
    if focus == "object" and motion in {"active", "moving"}:
        return "active_demonstration"
    if focus == "object":
        return "composition_hold"
    if focus == "mixed":
        return "mixed"
    if motion in {"active", "moving"}:
        return "visual_transition"
    return "unavailable"


def _state(frame, raw_index):
    focus = _focus(frame)
    motion = _motion_state(frame)
    text_present = frame.get("text_overlay") is True
    return {
        "frame": raw_index,
        "timestamp": float(frame.get("timestamp", raw_index) or raw_index),
        "focus": focus,
        "text": text_present,
        "composition": _composition(frame),
        "environment": _environment(frame),
        "motion": motion,
        "purpose": _purpose(focus, text_present, motion),
    }


def _same_visual_state(left, right):
    return all(left[key] == right[key] for key in ("focus", "text", "composition", "motion", "environment"))


def _has_persistent_multi_subject(frames, minimum_samples):
    run = 0
    for frame in frames:
        count = _number(frame, "subject_count", "person_count", "face_count")
        run = run + 1 if count >= 2 else 0
        if run >= minimum_samples:
            return True
    return False


def _candidate_states(states):
    groups = []
    for state in states:
        if groups and _same_visual_state(groups[-1]["states"][-1], state):
            groups[-1]["states"].append(state)
        else:
            groups.append({"states": [state]})
    return groups


def _group_summary(group):
    states = group["states"]
    return {
        "start_time": states[0]["timestamp"],
        "end_time": states[-1]["timestamp"] + 1.0,
        "supporting_frames": [state["frame"] for state in states],
        "focus": states[0]["focus"],
        "text": states[0]["text"],
        "composition": states[0]["composition"],
        "environment": states[0]["environment"],
        "motion": states[0]["motion"],
        "purpose": states[0]["purpose"],
    }


def _environment_continues(left, right):
    return left["environment"] == right["environment"] or "unavailable" in {left["environment"], right["environment"]}


def _subject_family(focus):
    return focus in {"person", "multiple_people", "alternating_subjects"}


def _compatible_semantic_purpose(left, right):
    if left["purpose"] == right["purpose"]:
        return True
    return _subject_family(left["focus"]) and _subject_family(right["focus"])


def _is_alternating_run(summaries, start, config):
    if start + config.alternating_min_states > len(summaries):
        return 0
    first = summaries[start]
    second = summaries[start + 1]
    if first["composition"] == second["composition"]:
        return 0
    if not (_subject_family(first["focus"]) and _subject_family(second["focus"])):
        return 0
    if first["text"] != second["text"] or not _environment_continues(first, second):
        return 0
    end = start + 2
    while end < len(summaries):
        expected = first if (end - start) % 2 == 0 else second
        current = summaries[end]
        if current["composition"] != expected["composition"]:
            break
        if current["text"] != first["text"] or not _subject_family(current["focus"]):
            break
        if not _environment_continues(first, current):
            break
        end += 1
    return end - start if end - start >= config.alternating_min_states else 0


def _merge_candidate_states(candidate_groups, config):
    summaries = [_group_summary(group) for group in candidate_groups]
    merged = []
    decisions = []
    alternating_patterns = []
    rejected = []
    index = 0
    while index < len(summaries):
        run_length = _is_alternating_run(summaries, index, config)
        if run_length:
            selected = summaries[index:index + run_length]
            merged.append({"parts": selected, "alternating": True})
            alternating_patterns.append({
                "candidate_indexes": list(range(index, index + run_length)),
                "pattern": "A-B-" + "-".join("A" if offset % 2 == 0 else "B" for offset in range(2, run_length)),
                "reason": "Repeated subject-focused views preserve environment, text role, and visual purpose.",
            })
            for boundary in range(index + 1, index + run_length):
                decisions.append({"boundary_after_candidate": boundary - 1, "decision": "merge", "reason": "alternating_state_continuity"})
            index += run_length
            continue

        current = summaries[index]
        if merged:
            prior = merged[-1]["parts"][-1]
            earlier = merged[-1]["parts"][-2] if len(merged[-1]["parts"]) >= 2 else None
            same_purpose = _compatible_semantic_purpose(prior, current)
            stable_context = _environment_continues(prior, current)
            text_stable = prior["text"] == current["text"]
            isolated_motion = (
                len(current["supporting_frames"]) <= config.brief_interruption_samples
                and prior["focus"] == current["focus"]
                and prior["text"] == current["text"]
                and prior["composition"] == current["composition"]
            )
            brief_return = False
            if index + 1 < len(summaries) and len(current["supporting_frames"]) <= config.brief_interruption_samples:
                following = summaries[index + 1]
                brief_return = (
                    prior["focus"] == following["focus"]
                    and prior["text"] == following["text"]
                    and _environment_continues(prior, following)
                    and _compatible_semantic_purpose(prior, following)
                )
            merge_reason = ""
            returned_after_brief_interruption = (
                earlier is not None
                and len(prior["supporting_frames"]) <= config.brief_interruption_samples
                and earlier["focus"] == current["focus"]
                and earlier["text"] == current["text"]
                and _environment_continues(earlier, current)
                and _compatible_semantic_purpose(earlier, current)
            )
            if returned_after_brief_interruption:
                merge_reason = "return_after_brief_interruption"
            elif isolated_motion:
                merge_reason = "isolated_motion_change"
            elif brief_return:
                merge_reason = "brief_interruption_return_to_prior_state"
            elif same_purpose and stable_context and text_stable:
                merge_reason = "same_semantic_purpose"
            if merge_reason:
                merged[-1]["parts"].append(current)
                decisions.append({"boundary_after_candidate": index - 1, "decision": "merge", "reason": merge_reason})
                rejected.append({"candidate_index": index, "reason": merge_reason})
                index += 1
                continue
        merged.append({"parts": [current], "alternating": False})
        if index:
            decisions.append({"boundary_after_candidate": index - 1, "decision": "keep", "reason": "persistent_semantic_purpose_change"})
        index += 1

    coalesced = []
    for item in merged:
        if coalesced:
            prior_item = coalesced[-1]
            prior_part = prior_item["parts"][-1]
            current_part = item["parts"][0]
            same_purpose = prior_part["purpose"] == current_part["purpose"]
            context_compatible = (
                prior_part["purpose"] == "text_led_context"
                or _environment_continues(prior_part, current_part)
            )
            if (
                same_purpose
                and prior_part["text"] == current_part["text"]
                and context_compatible
            ):
                prior_item["parts"].extend(item["parts"])
                prior_item["alternating"] = prior_item["alternating"] or item["alternating"]
                decisions.append({"boundary_after_candidate": None, "decision": "merge", "reason": "post_calibration_same_purpose"})
                continue
        coalesced.append(item)
    return coalesced, summaries, decisions, alternating_patterns, rejected


def _dominant(values):
    available = [value for value in values if value != "unavailable"]
    if not available:
        return "unavailable"
    return max(set(available), key=lambda value: (available.count(value), -available.index(value)))


def _beat_description(beat, position, total, prior_purposes):
    purpose = beat["purpose"]
    if beat["alternating"]:
        return "The edit alternates between visible subjects within the same visual setup."
    if purpose in prior_purposes:
        returns = {
            "environment_setup": "The sequence returns to an environment-led setup without introducing a new subject identity.",
            "subject_establishment": "The sequence returns to a subject-focused phase while keeping the description visually grounded.",
            "multi_subject_sequence": "Several visible subjects again share visual priority within one continuing phase.",
            "text_led_context": "Written information returns as the primary source of context in this later phase.",
            "visual_transition": "Sustained movement returns as the main visual function of this later phase.",
            "active_demonstration": "The sequence returns to an object-led phase with sustained visible movement.",
            "composition_hold": "The sequence returns to a held object-led composition.",
            "mixed": "Several visual elements again share priority within the same phase.",
            "unavailable": "This later phase still lacks enough evidence for a reliable visual purpose.",
        }
        return f"From {beat['start_time']:.0f}s, {returns[purpose][0].lower()}{returns[purpose][1:]}"
    descriptions = {
        "environment_setup": "The opening establishes the surrounding environment before a more specific visual focus appears.",
        "subject_establishment": "One visible subject carries the sequence as the main point of focus.",
        "multi_subject_sequence": "Several visible subjects share the sequence without one figure consistently carrying visual priority.",
        "text_led_context": "Written information becomes the primary source of context in this part of the opening.",
        "visual_transition": "A sustained change in movement creates a separate transition phase.",
        "active_demonstration": "A visible object remains central while sustained movement changes what the sequence is showing.",
        "composition_hold": "The opening holds on one object-led setup without changing its visual purpose.",
        "mixed": "Several visual elements share priority within the same opening phase.",
        "unavailable": "The available frames do not establish a reliable visual purpose for this phase.",
    }
    sentence = descriptions[purpose]
    if position == total - 1 and total > 1 and purpose == "subject_establishment":
        return "The final phase settles on one visible subject, creating a more singular visual priority."
    return sentence


def _semantic_beats(merged, confidence):
    beats = []
    prior_purposes = []
    for index, item in enumerate(merged):
        parts = item["parts"]
        focuses = [part["focus"] for part in parts]
        focus = "alternating_subjects" if item["alternating"] else _dominant(focuses)
        purposes = [part["purpose"] for part in parts]
        purpose = "multi_subject_sequence" if item["alternating"] else _dominant(purposes)
        text_values = [part["text"] for part in parts]
        frames = [frame for part in parts for frame in part["supporting_frames"]]
        beat = {
            "start_time": parts[0]["start_time"], "end_time": parts[-1]["end_time"],
            "focus": focus, "text": sum(text_values) >= max(1, len(text_values) / 2),
            "composition": "alternating_related_views" if item["alternating"] else _dominant([part["composition"] for part in parts]),
            "purpose": purpose, "frames": frames, "alternating": item["alternating"],
        }
        beats.append(SemanticBeat(
            start_time=beat["start_time"], end_time=beat["end_time"], dominant_focus=focus,
            text_presence=beat["text"], composition_state=beat["composition"],
            transition_type="opening" if index == 0 else "semantic_purpose_change",
            beat_purpose=purpose, semantic_description=_beat_description(beat, index, len(merged), prior_purposes),
            supporting_frames=frames, confidence=confidence,
        ))
        prior_purposes.append(purpose)
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


def _opening_summary(primary, clarity, progression, information, text_role, beats):
    if primary == "unavailable":
        return "The available frames do not establish a reliable visual focus, so the opening hierarchy remains unavailable."
    if primary == "alternating_subjects":
        start = "The opening alternates between visible subjects within the same visual setup."
    else:
        focus_phrase = {
            "person": "a visible person", "multiple_people": "several visible figures",
            "object": "one central object", "environment": "the surrounding environment",
            "text": "a written message", "mixed": "several visual elements",
        }[primary]
        clarity_phrase = {
            "immediate": "is clear from the first phase", "develops_early": "becomes clear within the early phases",
            "delayed": "does not become stable until later", "competing": "shares attention with competing elements",
            "unavailable": "cannot be timed reliably",
        }[clarity]
        start = f"The opening is led by {focus_phrase}, which {clarity_phrase}."
    progression_phrase = {
        "mostly_held": "The sequence largely holds one visual purpose.",
        "gradual_change": "The setup develops through one sustained change in visual purpose.",
        "frequent_change": "The sequence moves through several genuinely different visual purposes.",
        "distinct_beats": "The sequence progresses through clearly separated creative phases.",
        "unavailable": "The progression cannot be classified reliably.",
    }[progression]
    text_phrase = ""
    if information == "image_and_text":
        text_phrase = " Written cues share attention with the imagery."
    elif information == "text_led":
        text_phrase = " Written information carries most of the opening context."
    elif text_role == "absent":
        text_phrase = " The imagery carries the opening without written context."
    return f"{start} {progression_phrase}{text_phrase}"


def observe_semantics(frame_observations, metadata_context=None, config=None, temporal_evidence=None):
    config = config or DEFAULT_CALIBRATION
    frames = [dict(frame) for frame in frame_observations or [] if isinstance(frame, Mapping)]
    if not _has_persistent_multi_subject(frames, config.minimum_persistent_samples):
        for frame in frames:
            for key in ("subject_count", "person_count", "face_count"):
                if _number(frame, key) >= 2:
                    frame[key] = 1
    ordered = sorted(enumerate(frames), key=lambda item: float(item[1].get("timestamp", item[0]) or item[0]))
    states = [_state(frame, raw_index) for raw_index, frame in ordered]
    confidence = _confidence(frames)
    candidate_groups = _candidate_states(states)
    merged, candidates, decisions, alternating_patterns, rejected = _merge_candidate_states(candidate_groups, config)
    beats = _semantic_beats(merged, confidence)
    focuses = [state["focus"] for state in states]
    available_focuses = [focus for focus in focuses if focus != "unavailable"]

    has_alternating = bool(alternating_patterns)
    if has_alternating:
        primary = "alternating_subjects"
    elif not available_focuses:
        primary = "unavailable"
    elif "multiple_people" in available_focuses or len(set(available_focuses[:3])) >= 3:
        primary = "multiple_people" if "multiple_people" in available_focuses else "mixed"
    else:
        primary = _dominant(available_focuses)

    early = available_focuses[:3]
    if not early:
        clarity = "unavailable"
    elif primary in {"multiple_people", "mixed", "alternating_subjects"}:
        clarity = "competing"
    elif focuses and focuses[0] == primary:
        clarity = "immediate"
    elif primary in focuses[:3]:
        clarity = "develops_early"
    else:
        clarity = "delayed"

    text_flags = [state["text"] for state in states]
    text_count = sum(text_flags)
    explicit_text_confidences = [
        str(frame.get("text_overlay_confidence", "")).lower()
        for frame in frames if frame.get("text_overlay_confidence")
    ]
    text_evidence_confidence = (
        "limited" if explicit_text_confidences and "limited" in explicit_text_confidences
        else confidence
    )
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
        "person": "subject_first", "multiple_people": "subject_first", "alternating_subjects": "subject_first",
        "object": "subject_first", "text": "text_first", "environment": "environment_first",
        "mixed": "mixed", "unavailable": "unavailable",
    }[first_focus]
    if frames and _motion_state(frames[0]) == "active":
        opening_mode = "action_or_change_first"

    beat_count = len(beats)
    change_ratio = beat_count / len(frames) if frames else 0.0
    progression = (
        "unavailable" if not frames else "mostly_held" if beat_count == 1 else
        "gradual_change" if beat_count == 2 else
        "frequent_change" if beat_count >= config.frequent_change_min_beats and change_ratio >= config.frequent_change_ratio else
        "distinct_beats"
    )
    person_flags = [_subject_family(focus) for focus in focuses]
    if not frames or not any(person_flags):
        subject_pattern = "unavailable"
    elif has_alternating or "multiple_people" in focuses:
        subject_pattern = "multiple_subjects"
    elif person_flags[0] and sum(person_flags) >= max(1, len(frames) // 2):
        subject_pattern = "present_immediately"
    elif not person_flags[0] and any(person_flags[1:]):
        subject_pattern = "enters_later"
    else:
        subject_pattern = "inconsistent"

    evidence = [{
        "frame_index": state["frame"], "timestamp": state["timestamp"], "focus": state["focus"],
        "text_present": state["text"], "composition": state["composition"],
        "environment": state["environment"], "motion_state": state["motion"], "candidate_purpose": state["purpose"],
    } for state in states]
    unavailable = [name for name, value in (
        ("primary_visual_focus", primary), ("focus_clarity", clarity), ("opening_mode", opening_mode),
        ("visual_progression", progression), ("information_mode", information), ("text_role", text_role),
        ("subject_presence_pattern", subject_pattern),
    ) if value == "unavailable"]
    diagnostics = {
        "model": "frame_change -> visual_state_change -> semantic_beat_change",
        "persistence_thresholds": asdict(config),
        "candidate_frame_changes": [{"after_frame": states[i - 1]["frame"], "at_frame": states[i]["frame"]} for i in range(1, len(states)) if not _same_visual_state(states[i - 1], states[i])],
        "candidate_visual_state_boundaries": candidates,
        "final_semantic_boundaries": [{"beat_index": i, "start_time": beat.start_time, "end_time": beat.end_time, "beat_purpose": beat.beat_purpose} for i, beat in enumerate(beats)],
        "merge_decisions": decisions,
        "merge_reasons": sorted({decision["reason"] for decision in decisions if decision["decision"] == "merge"}),
        "alternating_patterns": alternating_patterns,
        "rejected_split_candidates": rejected,
        "temporal_evidence": temporal_evidence or {},
    }
    return SemanticObservation(
        version="observation-semantics-v2", primary_visual_focus=primary, focus_clarity=clarity,
        opening_mode=opening_mode, visual_progression=progression, information_mode=information,
        text_role=text_role, subject_presence_pattern=subject_pattern,
        opening_clarity_summary=_opening_summary(primary, clarity, progression, information, text_role, beats),
        semantic_confidence=confidence, supporting_evidence=evidence, beats=beats,
        unavailable_fields=unavailable, metadata_context=dict(metadata_context or {}),
        temporal_diagnostics=diagnostics,
        text_evidence_confidence=text_evidence_confidence,
    ).to_dict()
