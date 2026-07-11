from __future__ import annotations

import math
import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


UNKNOWN_VALUES = {
    None,
    "",
    "unknown",
    "unavailable",
    "not available",
}


def build_benchmark_signature(
    video: Optional[Mapping[str, Any]] = None,
    vision: Optional[Mapping[str, Any]] = None,
    understanding: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a neutral evidence signature for benchmark comparison.

    This module does not assign content categories or predefined formats.

    It only records evidence already available in Stratify:
    - metadata structure
    - duration
    - frame observations
    - visual observations
    - event evidence
    - temporal evidence
    - narrative evidence

    Missing evidence remains missing and is never guessed.
    """

    video = dict(video or {})
    vision = dict(vision or {})
    understanding = dict(understanding or {})

    title = _clean_text(video.get("title", ""))
    description = _clean_text(video.get("description", ""))
    duration_seconds = _duration_seconds(video.get("duration"))

    frame_observations = _as_list(
        vision.get("frame_observations")
    )

    events = _as_list(
        _nested_get(
            understanding,
            "events",
            "events",
            default=[],
        )
    )

    temporal = _as_dict(
        understanding.get("temporal")
    )

    narrative = _as_dict(
        understanding.get("narrative_draft")
        or understanding.get("narrative")
    )

    video_understanding = _as_dict(
        understanding.get("video")
    )

    frame_summary = _summarize_frame_observations(
        frame_observations
    )

    categorical_observations = {
        "visual_energy": _first_known(
            vision.get("visual_energy"),
            frame_summary.get("visual_energy"),
        ),
        "scene_type": _first_known(
            vision.get("scene_type"),
            frame_summary.get("scene_type"),
        ),
        "human_presence": _first_known(
            vision.get("human_presence"),
            frame_summary.get("human_presence"),
        ),
        "text_overlay": _first_known(
            vision.get("text_overlay"),
            frame_summary.get("text_overlay"),
        ),
        "dominant_lighting": _first_known(
            vision.get("dominant_lighting"),
            frame_summary.get("dominant_lighting"),
        ),
        "dominant_color_feel": _first_known(
            vision.get("dominant_color_feel"),
            frame_summary.get("dominant_color_feel"),
        ),
    }

    categorical_observations = {
        key: value
        for key, value in categorical_observations.items()
        if not _is_unknown(value)
    }

    narrative_evidence = {
        "main_subject": narrative.get("main_subject"),
        "opening_goal": narrative.get("opening_goal"),
        "viewer_expectation": narrative.get(
            "viewer_expectation"
        ),
        "story_promise": narrative.get("story_promise"),
        "unanswered_question": narrative.get(
            "unanswered_question"
        ),
        "narrative_progression": narrative.get(
            "narrative_progression"
        ),
    }

    narrative_evidence = {
        key: _clean_text(value)
        for key, value in narrative_evidence.items()
        if not _is_unknown(value)
    }

    temporal_text = _clean_text(
        temporal.get("summary")
        or video_understanding.get("summary")
        or understanding.get("summary")
    )

    evidence_count = 0
    evidence_count += int(bool(title))
    evidence_count += int(duration_seconds is not None)
    evidence_count += len(categorical_observations)
    evidence_count += int(bool(frame_observations))
    evidence_count += int(bool(events))
    evidence_count += len(narrative_evidence)
    evidence_count += int(bool(temporal_text))

    return {
        "version": "benchmark-signature-v1",
        "metadata": {
            "title": title,
            "description": description,
            "channel_title": _clean_text(
                video.get("channel_title", "")
            ),
            "duration_seconds": duration_seconds,
            "title_structure": _text_structure(title),
            "description_structure": _text_structure(
                description
            ),
        },
        "observations": categorical_observations,
        "behavior": {
            "frame_count": len(frame_observations),
            "event_count": len(events),
            "event_rate": _safe_rate(
                len(events),
                duration_seconds,
            ),
            "observation_change_rate": (
                _observation_change_rate(
                    frame_observations
                )
            ),
            "temporal_text": temporal_text,
        },
        "narrative": narrative_evidence,
        "availability": {
            "has_metadata": bool(title or description),
            "has_duration": duration_seconds is not None,
            "has_frames": bool(frame_observations),
            "has_events": bool(events),
            "has_temporal": bool(temporal_text),
            "has_narrative": bool(narrative_evidence),
            "evidence_count": evidence_count,
        },
    }


def compare_benchmark_signatures(
    reference: Mapping[str, Any],
    candidate: Mapping[str, Any],
    topic_score: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compare only evidence available on both sides.

    Missing fields are not treated as mismatches.

    Similarity and evidence coverage are reported separately.
    """

    components: List[Dict[str, Any]] = []

    reference_metadata = _as_dict(
        reference.get("metadata")
    )

    candidate_metadata = _as_dict(
        candidate.get("metadata")
    )

    _append_component(
        components=components,
        name="title_language_overlap",
        score=_text_similarity(
            reference_metadata.get("title", ""),
            candidate_metadata.get("title", ""),
        ),
        weight=1.2,
        available=bool(
            reference_metadata.get("title")
            and candidate_metadata.get("title")
        ),
    )

    if topic_score is not None:
        _append_component(
            components=components,
            name="retrieval_topic_overlap",
            score=_clamp(float(topic_score)),
            weight=1.0,
            available=True,
        )

    reference_duration = reference_metadata.get(
        "duration_seconds"
    )

    candidate_duration = candidate_metadata.get(
        "duration_seconds"
    )

    _append_component(
        components=components,
        name="duration_proximity",
        score=_duration_similarity(
            reference_duration,
            candidate_duration,
        ),
        weight=1.0,
        available=(
            reference_duration is not None
            and candidate_duration is not None
        ),
    )

    reference_title_structure = _as_dict(
        reference_metadata.get("title_structure")
    )

    candidate_title_structure = _as_dict(
        candidate_metadata.get("title_structure")
    )

    _append_component(
        components=components,
        name="title_structure",
        score=_structure_similarity(
            reference_title_structure,
            candidate_title_structure,
        ),
        weight=0.75,
        available=bool(
            reference_title_structure
            and candidate_title_structure
        ),
    )

    reference_observations = _as_dict(
        reference.get("observations")
    )

    candidate_observations = _as_dict(
        candidate.get("observations")
    )

    shared_observation_keys = sorted(
        set(reference_observations).intersection(
            candidate_observations
        )
    )

    if shared_observation_keys:
        observation_scores = [
            _value_similarity(
                reference_observations[key],
                candidate_observations[key],
            )
            for key in shared_observation_keys
        ]

        _append_component(
            components=components,
            name="shared_observations",
            score=(
                sum(observation_scores)
                / len(observation_scores)
            ),
            weight=1.5,
            available=True,
            evidence_keys=shared_observation_keys,
        )

    reference_behavior = _as_dict(
        reference.get("behavior")
    )

    candidate_behavior = _as_dict(
        candidate.get("behavior")
    )

    for key, weight in (
        ("event_rate", 1.3),
        ("observation_change_rate", 1.1),
    ):
        left_value = reference_behavior.get(key)
        right_value = candidate_behavior.get(key)

        _append_component(
            components=components,
            name=key,
            score=_numeric_similarity(
                left_value,
                right_value,
            ),
            weight=weight,
            available=(
                left_value is not None
                and right_value is not None
            ),
        )

    reference_temporal_text = reference_behavior.get(
        "temporal_text",
        "",
    )

    candidate_temporal_text = candidate_behavior.get(
        "temporal_text",
        "",
    )

    _append_component(
        components=components,
        name="temporal_language",
        score=_text_similarity(
            reference_temporal_text,
            candidate_temporal_text,
        ),
        weight=1.0,
        available=bool(
            reference_temporal_text
            and candidate_temporal_text
        ),
    )

    reference_narrative = _as_dict(
        reference.get("narrative")
    )

    candidate_narrative = _as_dict(
        candidate.get("narrative")
    )

    shared_narrative_keys = sorted(
        set(reference_narrative).intersection(
            candidate_narrative
        )
    )

    if shared_narrative_keys:
        narrative_scores = [
            _text_similarity(
                reference_narrative[key],
                candidate_narrative[key],
            )
            for key in shared_narrative_keys
        ]

        _append_component(
            components=components,
            name="shared_narrative",
            score=(
                sum(narrative_scores)
                / len(narrative_scores)
            ),
            weight=1.7,
            available=True,
            evidence_keys=shared_narrative_keys,
        )

    comparable_components = [
        item
        for item in components
        if item["available"]
    ]

    total_weight = sum(
        item["weight"]
        for item in comparable_components
    )

    if total_weight <= 0:
        compatibility_score = 0.0
    else:
        compatibility_score = sum(
            item["score"] * item["weight"]
            for item in comparable_components
        ) / total_weight

    possible_evidence_weight = 8.0

    evidence_coverage = min(
        total_weight / possible_evidence_weight,
        1.0,
    )

    reference_availability = _as_dict(
        reference.get("availability")
    )

    candidate_availability = _as_dict(
        candidate.get("availability")
    )

    both_have_observed_intro = bool(
        reference_availability.get("has_frames")
        and candidate_availability.get("has_frames")
    )

    confidence = _confidence_label(
        coverage_weight=evidence_coverage,
        both_have_observed_intro=(
            both_have_observed_intro
        ),
    )

    strongest_components = sorted(
        comparable_components,
        key=lambda item: (
            item["score"] * item["weight"]
        ),
        reverse=True,
    )[:3]

    weakest_components = sorted(
        comparable_components,
        key=lambda item: item["score"],
    )[:3]

    return {
        "compatibility_score": round(
            _clamp(compatibility_score),
            4,
        ),
        "evidence_coverage": round(
            evidence_coverage,
            4,
        ),
        "confidence": confidence,
        "both_intros_observed": (
            both_have_observed_intro
        ),
        "components": comparable_components,
        "strongest_evidence": [
            {
                "name": item["name"],
                "score": item["score"],
            }
            for item in strongest_components
        ],
        "weakest_evidence": [
            {
                "name": item["name"],
                "score": item["score"],
            }
            for item in weakest_components
        ],
    }


def minimum_signature_compatibility(
    reference_signature: Mapping[str, Any],
) -> float:
    """
    Select a threshold from available evidence.

    This does not use content categories or format rules.
    """

    availability = _as_dict(
        reference_signature.get("availability")
    )

    if (
        availability.get("has_frames")
        and availability.get("has_narrative")
    ):
        return 0.50

    if availability.get("has_duration"):
        return 0.44

    return 0.36


def _append_component(
    components: List[Dict[str, Any]],
    name: str,
    score: float,
    weight: float,
    available: bool,
    evidence_keys: Optional[Sequence[str]] = None,
) -> None:
    components.append(
        {
            "name": name,
            "score": round(_clamp(score), 4),
            "weight": float(weight),
            "available": bool(available),
            "evidence_keys": list(
                evidence_keys or []
            ),
        }
    )


def _clean_text(value: Any) -> str:
    text = str(value or "").lower()

    text = re.sub(
        r"https?://\S+",
        " ",
        text,
    )

    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
        flags=re.UNICODE,
    )

    text = re.sub(
        r"_+",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def _text_structure(text: str) -> Dict[str, float]:
    original = str(text or "")
    cleaned_words = _clean_text(original).split()

    character_count = len(original.strip())

    alphabetic_count = sum(
        character.isalpha()
        for character in original
    )

    return {
        "word_count": float(len(cleaned_words)),
        "character_count": float(character_count),
        "digit_ratio": _ratio(
            sum(
                character.isdigit()
                for character in original
            ),
            max(character_count, 1),
        ),
        "uppercase_ratio": _ratio(
            sum(
                character.isupper()
                for character in original
            ),
            max(alphabetic_count, 1),
        ),
        "separator_count": float(
            sum(
                original.count(separator)
                for separator in (
                    "|",
                    ":",
                    "-",
                    "•",
                )
            )
        ),
        "question_mark_count": float(
            original.count("?")
        ),
        "exclamation_mark_count": float(
            original.count("!")
        ),
    }


def _structure_similarity(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> float:
    shared_keys = set(left).intersection(right)

    if not shared_keys:
        return 0.0

    scores = [
        _numeric_similarity(
            left.get(key),
            right.get(key),
        )
        for key in shared_keys
    ]

    if not scores:
        return 0.0

    return sum(scores) / len(scores)


def _text_similarity(
    left: Any,
    right: Any,
) -> float:
    left_text = _clean_text(left)
    right_text = _clean_text(right)

    if not left_text or not right_text:
        return 0.0

    left_tokens = left_text.split()
    right_tokens = right_text.split()

    left_set = set(left_tokens)
    right_set = set(right_tokens)

    token_union = left_set.union(right_set)

    token_overlap = (
        len(left_set.intersection(right_set))
        / len(token_union)
        if token_union
        else 0.0
    )

    sequence_similarity = SequenceMatcher(
        None,
        left_text,
        right_text,
        autojunk=False,
    ).ratio()

    left_bigrams = set(
        zip(
            left_tokens,
            left_tokens[1:],
        )
    )

    right_bigrams = set(
        zip(
            right_tokens,
            right_tokens[1:],
        )
    )

    bigram_union = left_bigrams.union(
        right_bigrams
    )

    bigram_overlap = (
        len(
            left_bigrams.intersection(
                right_bigrams
            )
        )
        / len(bigram_union)
        if bigram_union
        else token_overlap
    )

    return _clamp(
        token_overlap * 0.50
        + sequence_similarity * 0.30
        + bigram_overlap * 0.20
    )


def _duration_similarity(
    left: Any,
    right: Any,
) -> float:
    if left is None or right is None:
        return 0.0

    left_value = max(float(left), 1.0)
    right_value = max(float(right), 1.0)

    distance = abs(
        math.log(
            left_value / right_value
        )
    )

    return math.exp(-distance)


def _numeric_similarity(
    left: Any,
    right: Any,
) -> float:
    if left is None or right is None:
        return 0.0

    try:
        left_value = float(left)
        right_value = float(right)
    except (TypeError, ValueError):
        return 0.0

    scale = max(
        abs(left_value),
        abs(right_value),
        1.0,
    )

    return _clamp(
        1.0
        - abs(left_value - right_value)
        / scale
    )


def _value_similarity(
    left: Any,
    right: Any,
) -> float:
    if _is_unknown(left) or _is_unknown(right):
        return 0.0

    if isinstance(left, bool) or isinstance(
        right,
        bool,
    ):
        return (
            1.0
            if bool(left) == bool(right)
            else 0.0
        )

    if (
        isinstance(left, (int, float))
        and isinstance(right, (int, float))
    ):
        return _numeric_similarity(
            left,
            right,
        )

    return _text_similarity(
        left,
        right,
    )


def _duration_seconds(
    value: Any,
) -> Optional[float]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return max(float(value), 0.0)

    raw_value = str(value).strip().upper()

    if not raw_value:
        return None

    if re.fullmatch(
        r"\d+(?:\.\d+)?",
        raw_value,
    ):
        return float(raw_value)

    match = re.fullmatch(
        r"P(?:(?P<days>\d+)D)?"
        r"(?:T(?:(?P<hours>\d+)H)?"
        r"(?:(?P<minutes>\d+)M)?"
        r"(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?",
        raw_value,
    )

    if not match:
        return None

    parts = match.groupdict()

    return (
        float(parts.get("days") or 0) * 86400
        + float(parts.get("hours") or 0) * 3600
        + float(parts.get("minutes") or 0) * 60
        + float(parts.get("seconds") or 0)
    )


def _summarize_frame_observations(
    frame_observations: Sequence[Any],
) -> Dict[str, Any]:
    if not frame_observations:
        return {}

    candidate_fields = (
        "visual_energy",
        "scene_type",
        "human_presence",
        "text_overlay",
        "dominant_lighting",
        "dominant_color_feel",
    )

    summary: Dict[str, Any] = {}

    for field in candidate_fields:
        values = []

        for observation in frame_observations:
            item = _as_dict(observation)
            value = item.get(field)

            if not _is_unknown(value):
                values.append(value)

        if values:
            summary[field] = _mode(values)

    return summary


def _observation_change_rate(
    frame_observations: Sequence[Any],
) -> Optional[float]:
    if len(frame_observations) < 2:
        return None

    normalized_observations = []

    for observation in frame_observations:
        item = _as_dict(observation)

        normalized_observations.append(
            tuple(
                sorted(
                    (
                        str(key),
                        _clean_text(value),
                    )
                    for key, value in item.items()
                    if not _is_unknown(value)
                )
            )
        )

    transition_count = sum(
        normalized_observations[index]
        != normalized_observations[index - 1]
        for index in range(
            1,
            len(normalized_observations),
        )
    )

    return (
        transition_count
        / max(
            len(normalized_observations) - 1,
            1,
        )
    )


def _safe_rate(
    count: int,
    duration_seconds: Optional[float],
) -> Optional[float]:
    if (
        duration_seconds is None
        or duration_seconds <= 0
    ):
        return None

    return (
        float(count)
        / float(duration_seconds)
    )


def _mode(
    values: Sequence[Any],
) -> Any:
    counts: Dict[
        str,
        Tuple[Any, int],
    ] = {}

    for value in values:
        key = repr(value)

        original_value, current_count = counts.get(
            key,
            (value, 0),
        )

        counts[key] = (
            original_value,
            current_count + 1,
        )

    return max(
        counts.values(),
        key=lambda item: item[1],
    )[0]


def _first_known(
    *values: Any,
) -> Any:
    for value in values:
        if not _is_unknown(value):
            return value

    return None


def _is_unknown(
    value: Any,
) -> bool:
    if isinstance(value, str):
        return (
            value.strip().lower()
            in UNKNOWN_VALUES
        )

    # Provider payloads are not always scalar. Structured values must not make
    # us discard the rest of an otherwise valid observation.
    if isinstance(value, (Mapping, list, tuple, set)):
        return False

    try:
        return value in UNKNOWN_VALUES
    except TypeError:
        return False


def _nested_get(
    source: Mapping[str, Any],
    *keys: str,
    default: Any = None,
) -> Any:
    current: Any = source

    for key in keys:
        if not isinstance(current, Mapping):
            return default

        current = current.get(key)

    if current is None:
        return default

    return current


def _as_dict(
    value: Any,
) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)

    if hasattr(
        value,
        "__dataclass_fields__",
    ):
        from dataclasses import asdict

        return asdict(value)

    return {}


def _as_list(
    value: Any,
) -> List[Any]:
    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    return []


def _ratio(
    numerator: float,
    denominator: float,
) -> float:
    if denominator <= 0:
        return 0.0

    return numerator / denominator


def _clamp(
    value: float,
) -> float:
    return max(
        0.0,
        min(float(value), 1.0),
    )


def _confidence_label(
    coverage_weight: float,
    both_have_observed_intro: bool,
) -> str:
    if (
        both_have_observed_intro
        and coverage_weight >= 0.70
    ):
        return "strong"

    if coverage_weight >= 0.48:
        return "moderate"

    return "limited"
