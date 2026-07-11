import ast
import json
import re
from typing import Any, Dict, Mapping, Sequence

from core.observers.observation_schema import (
    build_intro_observation_response,
    merge_observations,
    useful_field_count,
)
from core.providers.provider_router import observe_visual


CANONICAL_KEYS = {
    "opening_summary",
    "hook_type",
    "main_subject",
    "main_action",
    "setting",
    "visible_text",
    "emotion",
    "camera_framing",
    "central_conflict",
    "story_promise",
    "viewer_question",
    "possible_confusion",
    "first_impression",
    "confidence",
}

KEY_ALIASES = {
    "opening": "opening_summary",
    "summary": "opening_summary",
    "opening_description": "opening_summary",
    "hook": "hook_type",
    "subject": "main_subject",
    "primary_subject": "main_subject",
    "action": "main_action",
    "location": "setting",
    "environment": "setting",
    "text": "visible_text",
    "on_screen_text": "visible_text",
    "tone": "emotion",
    "emotional_tone": "emotion",
    "framing": "camera_framing",
    "conflict": "central_conflict",
    "promise": "story_promise",
    "audience_question": "viewer_question",
    "confusion": "possible_confusion",
    "viewer_confusion": "possible_confusion",
    "reaction": "first_impression",
    "first_time_viewer_reaction": "first_impression",
}


def _normalize_key(value: Any) -> str:
    key = str(value or "").strip().lower()

    key = re.sub(
        r"[^a-z0-9]+",
        "_",
        key,
    )

    key = re.sub(
        r"_+",
        "_",
        key,
    ).strip("_")

    return KEY_ALIASES.get(key, key)


def _strip_code_fences(text: Any) -> str:
    value = str(text or "").strip()

    value = re.sub(
        r"^\s*```(?:json|python)?\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )

    value = re.sub(
        r"\s*```\s*$",
        "",
        value,
    )

    return value.strip()


def _balanced_object(text: str) -> str:
    start = text.find("{")

    if start == -1:
        return ""

    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(text)):
        character = text[index]

        if in_string:
            if escaped:
                escaped = False

            elif character == "\\":
                escaped = True

            elif character == '"':
                in_string = False

            continue

        if character == '"':
            in_string = True

        elif character == "{":
            depth += 1

        elif character == "}":
            depth -= 1

            if depth == 0:
                return text[start:index + 1]

    return ""


def _repair_json(text: str) -> str:
    value = text.strip()

    value = (
        value
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )

    value = re.sub(
        r",\s*([}\]])",
        r"\1",
        value,
    )

    return value


def _parse_line_pairs(text: str) -> Dict[str, str]:
    parsed: Dict[str, str] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip().strip("-* ")

        match = re.match(
            r"^([A-Za-z][A-Za-z0-9 _-]{1,40})"
            r"\s*:\s*(.+)$",
            line,
        )

        if not match:
            continue

        key = _normalize_key(
            match.group(1)
        )

        value = (
            match.group(2)
            .strip()
            .strip('"\'')
        )

        if (
            key in CANONICAL_KEYS
            and value
        ):
            parsed[key] = value

    return parsed


def _canonicalize(
    source: Mapping[str, Any],
) -> Dict[str, Any]:
    result: Dict[str, Any] = {}

    nested_candidates = [
        source,
        source.get("observation"),
        source.get("analysis"),
        source.get("result"),
    ]

    for candidate in nested_candidates:
        if not isinstance(candidate, Mapping):
            continue

        for raw_key, raw_value in candidate.items():
            key = _normalize_key(raw_key)

            if key not in CANONICAL_KEYS:
                continue

            if isinstance(
                raw_value,
                (dict, list),
            ):
                value = json.dumps(
                    raw_value,
                    ensure_ascii=False,
                )
            else:
                value = str(
                    raw_value or ""
                ).strip()

            if value:
                result[key] = value

    return result


def extract_observation_object(
    text: Any,
) -> Dict[str, Any]:
    """
    Recover an observation from:

    - strict JSON
    - fenced JSON
    - Python-style dictionaries
    - key: value lines
    """

    cleaned = _strip_code_fences(text)

    if not cleaned:
        return {}

    candidates = [cleaned]

    balanced = _balanced_object(cleaned)

    if balanced and balanced != cleaned:
        candidates.insert(0, balanced)

    for candidate in candidates:
        repaired = _repair_json(candidate)

        try:
            parsed = json.loads(repaired)

            if isinstance(parsed, dict):
                return _canonicalize(parsed)

        except Exception:
            pass

        try:
            parsed = ast.literal_eval(repaired)

            if isinstance(parsed, dict):
                return _canonicalize(parsed)

        except Exception:
            pass

    line_pairs = _parse_line_pairs(cleaned)

    return _canonicalize(line_pairs)


def _compact_context(
    video: Mapping[str, Any] | None,
    vision: Mapping[str, Any] | None,
    understanding: Mapping[str, Any] | None,
) -> str:
    video = dict(video or {})
    vision = dict(vision or {})
    understanding = dict(
        understanding or {}
    )

    narrative = understanding.get(
        "narrative_draft",
        {},
    )

    if not isinstance(narrative, Mapping):
        narrative = {}

    temporal = understanding.get(
        "temporal",
        {},
    )

    if not isinstance(temporal, Mapping):
        temporal = {}

    events_container = understanding.get(
        "events",
        {},
    )

    if not isinstance(
        events_container,
        Mapping,
    ):
        events_container = {}

    events = events_container.get(
        "events",
        [],
    )

    if not isinstance(events, list):
        events = []

    context = {
        "title": video.get("title", ""),
        "description": str(
            video.get("description", "")
        )[:500],
        "visual_energy": vision.get(
            "visual_energy",
            "",
        ),
        "scene_type": vision.get(
            "scene_type",
            "",
        ),
        "human_presence": vision.get(
            "human_presence",
            "",
        ),
        "text_overlay": vision.get(
            "text_overlay",
            "",
        ),
        "temporal_summary": temporal.get(
            "summary",
            "",
        ),
        "event_count": len(events),
        "narrative_draft": {
            "main_subject": narrative.get(
                "main_subject",
                "",
            ),
            "opening_goal": narrative.get(
                "opening_goal",
                "",
            ),
            "viewer_expectation": narrative.get(
                "viewer_expectation",
                "",
            ),
            "story_promise": narrative.get(
                "story_promise",
                "",
            ),
            "narrative_progression": narrative.get(
                "narrative_progression",
                "",
            ),
        },
    }

    return json.dumps(
        context,
        ensure_ascii=False,
    )[:2200]


def _build_prompt(
    video: Mapping[str, Any] | None = None,
    vision: Mapping[str, Any] | None = None,
    understanding: Mapping[str, Any] | None = None,
    frame_count: int = 0,
) -> str:
    context = _compact_context(
        video=video,
        vision=vision,
        understanding=understanding,
    )

    return f"""
You are Stratify's evidence-first intro observer.

You are viewing {frame_count} frames sampled in chronological
order from the opening of one YouTube video.

Use the frames as the primary evidence.

The supplied context is supporting evidence produced by
Stratify's existing pipeline.

Do not invent details.

Important rules:

- Do not recommend improvements.
- Do not predict views, retention, or virality.
- Do not assign a predefined content category.
- Do not call something unknown when the title or visible
  sequence provides reasonable evidence.
- When a field is genuinely unsupported, use "unknown".
- Keep every field to one short sentence or phrase.
- Return one JSON object only.
- Do not return markdown.
- Do not include commentary outside the JSON.

Existing evidence:

{context}

Return exactly these keys:

{{
  "opening_summary": "",
  "hook_type": "",
  "main_subject": "",
  "main_action": "",
  "setting": "",
  "visible_text": "",
  "emotion": "",
  "camera_framing": "",
  "central_conflict": "",
  "story_promise": "",
  "viewer_question": "",
  "possible_confusion": "",
  "first_impression": "",
  "confidence": "low"
}}

Field meaning:

- opening_summary:
  What the opening sequence establishes.

- hook_type:
  The observable attention mechanism, described naturally.

- main_subject:
  The clearest person, object, place, event, or idea.

- main_action:
  What visibly happens across the sequence.

- central_conflict:
  The tension or opposition visible or strongly implied.

- story_promise:
  What continued viewing appears likely to deliver.

- viewer_question:
  The main question created for a first-time viewer.

- first_impression:
  The likely immediate impression of the opening.

- confidence:
  high, moderate, or low.
""".strip()


def observe_visual_intro(
    frame_data_urls: Sequence[str],
    video: Mapping[str, Any] | None = None,
    vision: Mapping[str, Any] | None = None,
    understanding: Mapping[str, Any] | None = None,
    fallback_observation: Mapping[str, Any] | None = None,
    timeout_seconds: int = 45,
) -> Dict[str, Any]:
    if not frame_data_urls:
        return build_intro_observation_response(
            status="unavailable",
            observation=(
                fallback_observation or {}
            ),
            provider="evidence_fallback",
            warnings=[
                "No frames were available for visual observation."
            ],
        )

    provider_result = observe_visual(
        prompt=_build_prompt(
            video=video,
            vision=vision,
            understanding=understanding,
            frame_count=len(
                frame_data_urls
            ),
        ),
        frame_data_urls=list(
            frame_data_urls
        ),
        timeout_seconds=timeout_seconds,
    )

    warnings = list(
        provider_result.get(
            "warnings"
        )
        or []
    )

    provider_warning = provider_result.get(
        "warning"
    )

    if provider_warning:
        provider_warning = str(
            provider_warning
        )

        if provider_warning not in warnings:
            warnings.append(
                provider_warning
            )

    raw_content = provider_result.get(
        "content",
        "",
    )

    parsed = extract_observation_object(
        raw_content
    )

    merged = merge_observations(
        parsed,
        fallback_observation or {},
    )

    useful_count = useful_field_count(
        merged
    )

    if (
        provider_result.get("status")
        == "success"
        and parsed
    ):
        if useful_count < 4:
            warnings.append(
                "The visual provider returned sparse evidence. "
                "Stratify filled unsupported fields from "
                "existing pipeline evidence."
            )

        return build_intro_observation_response(
            status="success",
            observation=merged,
            provider=provider_result.get(
                "provider",
                "",
            ),
            warnings=warnings,
            raw_content=raw_content,
        )

    warnings.append(
        "Visual AI output was unavailable or could not be "
        "parsed. Stratify used existing pipeline evidence."
    )

    fallback_status = (
        "success"
        if useful_count >= 3
        else "unavailable"
    )

    return build_intro_observation_response(
        status=fallback_status,
        observation=merged,
        provider="evidence_fallback",
        warnings=warnings,
        raw_content=raw_content,
    )