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
    visual_anchor = _map(focus, {
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
        reveal_pattern=_map(clarity, {
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
    evidence = []
    for key in ("opening_mode", "primary_visual_focus", "visual_progression", "information_mode", "text_role"):
        value = _value(observation, key)
        if value != "unavailable":
            evidence.append({"semantic_field": key, "observed_value": value})
    beats = _beats(observation)
    if beats:
        evidence.append({"semantic_field": "beats", "observed_value": len(beats)})
    components = []
    if structure.opening_strategy != "unavailable":
        components.append(f"uses a {structure.opening_strategy} organization")
    if structure.reveal_pattern != "unavailable":
        components.append(structure.reveal_pattern)
    if structure.attention_evolution != "unavailable":
        components.append(structure.attention_evolution)
    summary = "The opening " + ", then ".join(components) + "." if components else "The available observations do not establish how the opening is organized."
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
