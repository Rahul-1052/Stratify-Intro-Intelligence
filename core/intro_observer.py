import base64
from io import BytesIO

from PIL import Image

from core.observers.visual_observer import observe_visual_intro
from core.observers.story_observer import observe_story
from core.observers.audience_observer import observe_audience
from core.observers.observation_schema import build_intro_observation_response


MAX_AI_OBSERVER_FRAMES = 2
MAX_IMAGE_SIZE = 448
JPEG_QUALITY = 70


def _sample_frames(frame_paths, max_frames=MAX_AI_OBSERVER_FRAMES):
    paths = list(frame_paths or [])

    if len(paths) <= max_frames:
        return paths

    if max_frames <= 1:
        return [paths[0]]

    step = (len(paths) - 1) / (max_frames - 1)
    indexes = [round(i * step) for i in range(max_frames)]

    return [paths[index] for index in indexes]


def _frame_to_data_url(frame_path):
    with Image.open(frame_path) as image:
        image = image.convert("RGB")
        image.thumbnail((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE))

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)

    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


def observe_intro(frame_paths, video=None, timeout_seconds=30):
    if not frame_paths:
        return build_intro_observation_response(
            status="unavailable",
            observation={},
            provider="",
            warnings=["No intro frames supplied."],
        )

    sampled_paths = _sample_frames(frame_paths)

    try:
        frame_data_urls = [_frame_to_data_url(path) for path in sampled_paths]
    except Exception as exc:
        return build_intro_observation_response(
            status="failed",
            observation={},
            provider="",
            warnings=[f"Unable to read intro frames: {exc}"],
        )

    visual = observe_visual_intro(
        frame_data_urls=frame_data_urls,
        video=video,
        timeout_seconds=timeout_seconds,
    )

    if visual.get("status") != "success":
        return visual

    observation = visual.get("observation", {})

    story = observe_story(observation)
    observation.update(story)

    audience = observe_audience(observation)
    observation.update(audience)

    return build_intro_observation_response(
        status="success",
        observation=observation,
        provider=visual.get("provider", ""),
        warnings=visual.get("warnings", []),
    )