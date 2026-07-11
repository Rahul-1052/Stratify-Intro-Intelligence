"""Canonical observation schema for Stratify's intro observation layer."""

from copy import deepcopy
from typing import Any, Dict, Mapping


DEFAULT_OBSERVATION = {
    "opening_summary": "unknown",
    "hook_type": "unknown",
    "main_subject": "unknown",
    "main_action": "unknown",
    "setting": "unknown",
    "visible_text": "none visible",
    "emotion": "unknown",
    "camera_framing": "unknown",
    "central_conflict": "unknown",
    "story_promise": "unknown",
    "viewer_question": "unknown",
    "possible_confusion": "unknown",
    "first_impression": "unknown",
    "confidence": "low",
}

UNKNOWN_VALUES = {
    "",
    "unknown",
    "unclear",
    "not clear",
    "not visible",
    "not available",
    "unavailable",
    "n/a",
    "none",
    "null",
}


def empty_observation() -> Dict[str, str]:
    return deepcopy(DEFAULT_OBSERVATION)


def is_unknown(value: Any) -> bool:
    if value is None:
        return True

    text = str(value).strip().lower()
    return text in UNKNOWN_VALUES


def normalize_confidence(value: Any) -> str:
    text = str(value or "").strip().lower()

    if text in {"high", "strong"}:
        return "high"

    if text in {"moderate", "medium"}:
        return "moderate"

    return "low"


def normalize_observation(
    observation: Mapping[str, Any] | None,
) -> Dict[str, str]:
    """
    Ensure every canonical observation key exists.

    Extra provider keys are ignored.
    """

    result = empty_observation()

    if not isinstance(observation, Mapping):
        return result

    for key in result:
        if key == "confidence":
            result[key] = normalize_confidence(
                observation.get(key)
            )
            continue

        value = observation.get(key)

        if value is None:
            continue

        text = " ".join(str(value).split()).strip()

        if text:
            result[key] = text

    if is_unknown(result.get("visible_text")):
        result["visible_text"] = "none visible"

    return result


def merge_observations(
    primary: Mapping[str, Any] | None,
    fallback: Mapping[str, Any] | None,
) -> Dict[str, str]:
    """
    Preserve useful primary evidence and fill only unknown fields
    from the fallback evidence.
    """

    primary_normalized = normalize_observation(primary)
    fallback_normalized = normalize_observation(fallback)

    merged = dict(primary_normalized)

    for key, fallback_value in fallback_normalized.items():
        if key == "confidence":
            continue

        if (
            is_unknown(merged.get(key))
            and not is_unknown(fallback_value)
        ):
            merged[key] = fallback_value

    confidence_rank = {
        "low": 0,
        "moderate": 1,
        "high": 2,
    }

    primary_confidence = normalize_confidence(
        primary_normalized.get("confidence")
    )

    fallback_confidence = normalize_confidence(
        fallback_normalized.get("confidence")
    )

    merged["confidence"] = max(
        (
            primary_confidence,
            fallback_confidence,
        ),
        key=lambda item: confidence_rank[item],
    )

    return normalize_observation(merged)


def useful_field_count(
    observation: Mapping[str, Any] | None,
) -> int:
    normalized = normalize_observation(observation)

    excluded = {
        "confidence",
        "visible_text",
    }

    return sum(
        1
        for key, value in normalized.items()
        if key not in excluded
        and not is_unknown(value)
    )


def build_intro_observation_response(
    status: str,
    observation: Mapping[str, Any] | None,
    provider: str = "",
    warnings: list[str] | None = None,
    raw_content: str = "",
) -> Dict[str, Any]:
    return {
        "status": status,
        "provider": provider,
        "observation": normalize_observation(
            observation
        ),
        "warnings": warnings or [],
        "raw_content": str(
            raw_content or ""
        )[:2000],
    }