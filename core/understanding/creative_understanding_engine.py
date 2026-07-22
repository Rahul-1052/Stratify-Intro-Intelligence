"""Deterministic conversion from semantic observations to creative understanding."""

from typing import Any, Mapping, Sequence, Tuple

from core.understanding.creative_structure import CreativeStructure
from core.understanding.creative_understanding import CreativeUnderstanding


def _value(observation, key):
    value = observation.get(key)
    return value if isinstance(value, str) and value else "unavailable"


def _beats(observation):
    value = observation.get("beats", [])
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [beat for beat in value if isinstance(beat, Mapping)]


def _map(value, choices):
    return choices.get(value, "unavailable")


def build_creative_structure(semantic_observation: Mapping[str, Any] | None) -> CreativeStructure:
    """Describe organization using only existing semantic-observation fields."""
    observation = semantic_observation if isinstance(semantic_observation, Mapping) else {}
    beats = _beats(observation)
    purposes = [str(beat.get("beat_purpose", "unavailable")) for beat in beats]
    transitions = [str(beat.get("transition_type", "unavailable")) for beat in beats[1:]]
    focus = _value(observation, "primary_visual_focus")
    clarity = _value(observation, "focus_clarity")
    opening_mode = _value(observation, "opening_mode")
    progression = _value(observation, "visual_progression")
    information = _value(observation, "information_mode")
    text_role = _value(observation, "text_role")

    opening_strategy = _map(opening_mode, {
        "subject_first": "subject-first", "text_first": "text-first",
        "environment_first": "context-first", "action_or_change_first": "change-first",
        "mixed": "multi-element opening",
    })
    anchor_focus = focus
    effective_clarity = clarity
    if opening_mode == "environment_first" and len(beats) > 1:
        later_focuses = [str(beat.get("dominant_focus", "unavailable")) for beat in beats[1:]]
        later_anchor = next((value for value in reversed(later_focuses) if value not in {"environment", "unavailable"}), None)
        if later_anchor:
            anchor_focus = later_anchor
            effective_clarity = "delayed" if later_anchor != focus else clarity
    visual_anchor = _map(anchor_focus, {
        "person": "single subject", "multiple_people": "multiple subjects",
        "alternating_subjects": "alternating subjects", "object": "object",
        "environment": "environment", "text": "written information", "mixed": "mixed elements",
    })
    known_purposes = [purpose for purpose in purposes if purpose != "unavailable"]
    confidence = _value(observation, "semantic_confidence")
    if confidence not in {"high", "moderate", "limited"}:
        confidence = "limited"
    return CreativeStructure(
        opening_strategy=opening_strategy,
        information_order=_map(information, {
            "image_led": "visual information leads", "text_led": "written information leads",
            "image_and_text": "visual and written information arrive together",
        }),
        visual_anchor=visual_anchor,
        attention_evolution=_map(progression, {
            "mostly_held": "holds one visual purpose", "gradual_change": "develops through one sustained change",
            "distinct_beats": "moves through distinct phases", "frequent_change": "moves through frequent purpose changes",
        }),
        structural_rhythm=("single phase" if len(beats) == 1 else "two-part progression" if len(beats) == 2 else "multi-phase progression" if len(beats) >= 3 else "unavailable"),
        information_density=_map(text_role, {
            "absent": "image-only information", "intermittent": "layered at selected moments",
            "persistent": "continuously layered", "dominant": "written-information dense",
        }),
        reveal_pattern=_map(effective_clarity, {
            "immediate": "anchor established immediately", "develops_early": "anchor develops early",
            "delayed": "anchor revealed later", "competing": "multiple anchors remain in play",
        }),
        transition_style=("semantic phase changes" if transitions and all(item == "semantic_purpose_change" for item in transitions) else "mixed or unavailable transitions" if transitions else "no observed phase transition"),
        structural_consistency=("repeated purpose" if len(known_purposes) > 1 and len(set(known_purposes)) == 1 else "purpose changes across phases" if len(set(known_purposes)) > 1 else "single established purpose" if len(known_purposes) == 1 else "unavailable"),
        creative_emphasis=_map(information, {
            "image_led": f"visual emphasis on {visual_anchor}" if visual_anchor != "unavailable" else "visual emphasis",
            "text_led": "written-information emphasis", "image_and_text": "shared visual and written emphasis",
        }),
        confidence=confidence,
    )


def build_creative_understanding(structure, semantic_observation=None):
    observation = semantic_observation if isinstance(semantic_observation, Mapping) else {}
    text_confidence = _value(observation, "text_evidence_confidence")
    evidence = []
    for key in ("opening_mode", "primary_visual_focus", "visual_progression", "information_mode", "text_role"):
        value = _value(observation, key)
        if value != "unavailable":
            evidence.append({"semantic_field": key, "observed_value": value})
    beats = _beats(observation)
    if beats:
        evidence.append({"semantic_field": "beats", "observed_value": len(beats)})
    strategy = {
        "subject-first": "starts subject-first",
        "context-first": "starts context-first",
        "text-first": "starts text-first",
        "change-first": "starts change-first with visible action or change",
        "multi-element opening": "starts with a multi-element opening",
    }.get(structure.opening_strategy)
    reveal = {
        "anchor established immediately": f"the {structure.visual_anchor} is established immediately",
        "anchor develops early": f"the {structure.visual_anchor} becomes established early",
        "anchor revealed later": f"the {structure.visual_anchor} is introduced later",
        "multiple anchors remain in play": "multiple visual anchors remain in play",
    }.get(structure.reveal_pattern)
    evolution = {
        "holds one visual purpose": "the sequence holds one visual purpose",
        "develops through one sustained change": "the sequence develops through one sustained change",
        "moves through distinct phases": "the sequence moves through distinct phases",
        "moves through frequent purpose changes": "the sequence moves through frequent purpose changes",
    }.get(structure.attention_evolution)
    density = {
        "image-only information": "without written information",
        "layered at selected moments": "with written information layered at selected moments",
        "continuously layered": "with written and visual information layered continuously",
        "written-information dense": "with written information carrying dense structural emphasis",
    }.get(structure.information_density)
    if density and structure.information_density != "image-only information" and text_confidence == "limited":
        density = "with possible written information indicated by limited visual evidence"
    components = [value for value in (strategy, reveal, evolution) if value]
    summary = "The opening " + "; ".join(components) + (f", {density}" if density else "") + "." if components else "The available observations do not establish how the opening is organized."
    structural_parts = [value for value in (structure.structural_rhythm, structure.information_order, structure.transition_style) if value != "unavailable"]
    strength = "strong" if len(evidence) >= 6 and structure.confidence == "high" else "moderate" if len(evidence) >= 3 and structure.confidence in {"high", "moderate"} else "limited"
    return CreativeUnderstanding(
        summary=summary, primary_strategy=structure.opening_strategy,
        structural_summary="; ".join(structural_parts) if structural_parts else "unavailable",
        supporting_evidence=evidence, evidence_strength=strength, confidence=structure.confidence,
    )


def understand_creative_opening(semantic_observation: Mapping[str, Any] | None) -> Tuple[CreativeStructure, CreativeUnderstanding]:
    structure = build_creative_structure(semantic_observation)
    return structure, build_creative_understanding(structure, semantic_observation)
