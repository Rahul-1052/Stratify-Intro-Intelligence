import base64
from io import BytesIO
from typing import Any, Dict, Mapping, Sequence

from PIL import Image

from core.observers.audience_observer import (
    observe_audience,
)
from core.observers.observation_schema import (
    build_intro_observation_response,
    is_unknown,
    merge_observations,
    normalize_observation,
    useful_field_count,
)
from core.observers.story_observer import (
    observe_story,
)
from core.observers.visual_observer import (
    observe_visual_intro,
)


MAX_AI_OBSERVER_FRAMES = 6
MAX_IMAGE_SIZE = 640
JPEG_QUALITY = 78


def _sample_frames(
    frame_paths: Sequence[str],
    max_frames: int = MAX_AI_OBSERVER_FRAMES,
) -> list[str]:
    paths = list(frame_paths or [])

    if len(paths) <= max_frames:
        return paths

    if max_frames <= 1:
        return [paths[0]]

    step = (
        len(paths) - 1
    ) / (
        max_frames - 1
    )

    indexes = [
        round(index * step)
        for index in range(max_frames)
    ]

    sampled = []
    seen = set()

    for index in indexes:
        path = paths[index]

        if path not in seen:
            sampled.append(path)
            seen.add(path)

    return sampled


def _frame_to_data_url(
    frame_path: str,
) -> str:
    with Image.open(frame_path) as image:
        image = image.convert("RGB")

        image.thumbnail(
            (
                MAX_IMAGE_SIZE,
                MAX_IMAGE_SIZE,
            )
        )

        buffer = BytesIO()

        image.save(
            buffer,
            format="JPEG",
            quality=JPEG_QUALITY,
            optimize=True,
        )

        encoded = base64.b64encode(
            buffer.getvalue()
        ).decode("utf-8")

    return (
        "data:image/jpeg;base64,"
        + encoded
    )


def _text(value: Any) -> str:
    return " ".join(
        str(value or "").split()
    ).strip()


def _known(value: Any) -> bool:
    return not is_unknown(value)


def _first_known(
    *values: Any,
) -> str:
    for value in values:
        if _known(value):
            return _text(value)

    return "unknown"


def _narrative(
    understanding: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    understanding = dict(
        understanding or {}
    )

    value = (
        understanding.get(
            "narrative_draft"
        )
        or understanding.get(
            "narrative"
        )
        or {}
    )

    if isinstance(value, Mapping):
        return dict(value)

    return {}


def _event_count(
    understanding: Mapping[str, Any] | None,
) -> int:
    understanding = dict(
        understanding or {}
    )

    events_container = understanding.get(
        "events",
        {},
    )

    if not isinstance(
        events_container,
        Mapping,
    ):
        return 0

    events = events_container.get(
        "events",
        [],
    )

    if not isinstance(events, list):
        return 0

    return len(events)


def _build_evidence_fallback(
    video: Mapping[str, Any] | None,
    vision: Mapping[str, Any] | None,
    understanding: Mapping[str, Any] | None,
) -> Dict[str, str]:
    """
    Build a fallback only from evidence already produced by
    Stratify.

    No predefined content categories or domain-specific rules
    are used.
    """

    video = dict(video or {})
    vision = dict(vision or {})
    understanding = dict(
        understanding or {}
    )

    narrative = _narrative(
        understanding
    )

    title = _text(
        video.get("title")
    )

    temporal = understanding.get(
        "temporal",
        {},
    )

    if not isinstance(temporal, Mapping):
        temporal = {}

    video_understanding = understanding.get(
        "video",
        {},
    )

    if not isinstance(
        video_understanding,
        Mapping,
    ):
        video_understanding = {}

    temporal_summary = _text(
        temporal.get("summary")
    )

    unified_summary = _text(
        understanding.get("summary")
    )

    video_summary = _text(
        video_understanding.get(
            "summary"
        )
    )

    visual_energy = _text(
        vision.get("visual_energy")
    )

    scene_type = _text(
        vision.get("scene_type")
    )

    text_overlay = vision.get(
        "text_overlay"
    )

    event_count = _event_count(
        understanding
    )

    main_subject = _first_known(
        narrative.get("main_subject"),
        title,
    )

    opening_summary = _first_known(
        narrative.get("opening_goal"),
        temporal_summary,
        video_summary,
        unified_summary,
    )

    if is_unknown(opening_summary):
        evidence_parts = []

        if _known(scene_type):
            evidence_parts.append(
                f"a {scene_type} opening"
            )

        if _known(visual_energy):
            evidence_parts.append(
                f"{visual_energy} visual energy"
            )

        if event_count:
            event_label = (
                "change"
                if event_count == 1
                else "changes"
            )

            evidence_parts.append(
                f"{event_count} observable "
                f"{event_label}"
            )

        if evidence_parts:
            opening_summary = (
                "The intro establishes "
                + ", with ".join(
                    evidence_parts
                )
                + "."
            )

        elif title:
            opening_summary = (
                "The opening introduces the "
                "subject promised by the title: "
                f"{title}."
            )

        else:
            opening_summary = "unknown"

    main_action = _first_known(
        temporal_summary,
        narrative.get(
            "narrative_progression"
        ),
    )

    if is_unknown(main_action):
        if event_count:
            event_label = (
                "change"
                if event_count == 1
                else "changes"
            )

            main_action = (
                "The opening moves through "
                f"{event_count} observable "
                f"visual {event_label}."
            )

        elif _known(visual_energy):
            main_action = (
                "The opening relies on "
                f"{visual_energy} visual movement."
            )

    hook_type = "unknown"

    if event_count >= 2:
        hook_type = (
            "A changing visual sequence creates "
            "the initial attention."
        )

    elif _known(visual_energy):
        hook_type = (
            "The opening uses "
            f"{visual_energy} visual energy "
            "as its attention cue."
        )

    elif title:
        hook_type = (
            "The opening relies on the title's "
            "promised subject for initial interest."
        )

    story_promise = _first_known(
        narrative.get("story_promise"),
        narrative.get(
            "viewer_expectation"
        ),
    )

    if (
        is_unknown(story_promise)
        and title
    ):
        story_promise = (
            "Continued viewing appears intended "
            f"to deliver on: {title}."
        )

    viewer_question = _first_known(
        narrative.get(
            "unanswered_question"
        )
    )

    if (
        is_unknown(viewer_question)
        and title
    ):
        viewer_question = (
            "How will the opening develop "
            f"the promise of '{title}'?"
        )

    setting = _first_known(
        scene_type
    )

    visible_text = "none visible"

    if text_overlay is True:
        visible_text = (
            "Text is present, but the current "
            "evidence does not reliably "
            "transcribe it."
        )

    first_impression = _first_known(
        opening_summary
    )

    possible_confusion = "none obvious"

    unclear = []

    if is_unknown(main_subject):
        unclear.append("main subject")

    if is_unknown(story_promise):
        unclear.append("story promise")

    if unclear:
        possible_confusion = (
            "A first-time viewer may not "
            "immediately understand the "
            + " and ".join(unclear)
            + "."
        )

    confidence = "moderate"

    temporary_observation = {
        "opening_summary": opening_summary,
        "main_subject": main_subject,
        "main_action": main_action,
        "story_promise": story_promise,
        "viewer_question": viewer_question,
    }

    if useful_field_count(
        temporary_observation
    ) < 3:
        confidence = "low"

    return normalize_observation(
        {
            "opening_summary": (
                opening_summary
            ),
            "hook_type": hook_type,
            "main_subject": main_subject,
            "main_action": main_action,
            "setting": setting,
            "visible_text": visible_text,
            "emotion": _first_known(
                narrative.get(
                    "emotional_tone"
                )
            ),
            "camera_framing": "unknown",
            "central_conflict": (
                _first_known(
                    narrative.get(
                        "central_conflict"
                    )
                )
            ),
            "story_promise": (
                story_promise
            ),
            "viewer_question": (
                viewer_question
            ),
            "possible_confusion": (
                possible_confusion
            ),
            "first_impression": (
                first_impression
            ),
            "confidence": confidence,
        }
    )


def observe_intro(
    frame_paths: Sequence[str],
    video: Mapping[str, Any] | None = None,
    vision: Mapping[str, Any] | None = None,
    understanding: Mapping[str, Any] | None = None,
    timeout_seconds: int = 45,
) -> Dict[str, Any]:
    fallback = _build_evidence_fallback(
        video=video,
        vision=vision,
        understanding=understanding,
    )

    if not frame_paths:
        fallback_status = (
            "success"
            if useful_field_count(
                fallback
            ) >= 3
            else "unavailable"
        )

        return build_intro_observation_response(
            status=fallback_status,
            observation=fallback,
            provider="evidence_fallback",
            warnings=[
                "No intro frames were supplied. "
                "Existing pipeline evidence was used."
            ],
        )

    sampled_paths = _sample_frames(
        frame_paths
    )

    try:
        frame_data_urls = [
            _frame_to_data_url(path)
            for path in sampled_paths
        ]

    except Exception as exc:
        fallback_status = (
            "success"
            if useful_field_count(
                fallback
            ) >= 3
            else "failed"
        )

        return build_intro_observation_response(
            status=fallback_status,
            observation=fallback,
            provider="evidence_fallback",
            warnings=[
                f"Unable to read intro frames: {exc}",
                "Existing pipeline evidence was used.",
            ],
        )

    visual_result = observe_visual_intro(
        frame_data_urls=frame_data_urls,
        video=video,
        vision=vision,
        understanding=understanding,
        fallback_observation=fallback,
        timeout_seconds=timeout_seconds,
    )

    observation = normalize_observation(
        visual_result.get(
            "observation",
            {},
        )
    )

    observation = merge_observations(
        observation,
        fallback,
    )

    observation.update(
        observe_story(observation)
    )

    observation = merge_observations(
        observation,
        fallback,
    )

    observation.update(
        observe_audience(observation)
    )

    observation = merge_observations(
        observation,
        fallback,
    )

    status = (
        "success"
        if useful_field_count(
            observation
        ) >= 3
        else visual_result.get(
            "status",
            "unavailable",
        )
    )

    return build_intro_observation_response(
        status=status,
        observation=observation,
        provider=visual_result.get(
            "provider",
            "evidence_fallback",
        ),
        warnings=visual_result.get(
            "warnings",
            [],
        ),
        raw_content=visual_result.get(
            "raw_content",
            "",
        ),
    )