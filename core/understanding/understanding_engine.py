from typing import Any, Dict

from core.understanding.event_understanding import understand_intro_events
from core.understanding.temporal_understanding import understand_temporal_flow
from core.understanding.video_understanding import understand_video_intro


def build_intro_understanding(
    video: Dict[str, Any],
    vision: Dict[str, Any],
    intro_duration: float = 15.0,
) -> Dict[str, Any]:
    """
    Single orchestration point for intro understanding.

    This engine combines:
    - visual/video understanding
    - canonical event understanding
    - temporal flow understanding

    It does not compare, score, recommend, or generate final reports.
    """

    frame_observations = vision.get("frame_observations", [])
    video_id = video.get("video_id", "")

    video_result = understand_video_intro(
        video_id=video_id,
        frame_observations=frame_observations,
        intro_duration=intro_duration,
        metadata=video,
    )

    events_result = understand_intro_events(frame_observations)

    temporal_result = understand_temporal_flow(frame_observations)

    return {
        "status": "success" if frame_observations else "unavailable",
        "video": _to_dict(video_result),
        "events": events_result,
        "temporal": temporal_result,
        "summary": _build_unified_summary(
            video_result=_to_dict(video_result),
            events_result=events_result,
            temporal_result=temporal_result,
        ),
    }


def _build_unified_summary(
    video_result: Dict[str, Any],
    events_result: Dict[str, Any],
    temporal_result: Dict[str, Any],
) -> str:
    return (
        f"{video_result.get('summary', '')} "
        f"{events_result.get('summary', '')} "
        f"{temporal_result.get('summary', '')}"
    ).strip()


def _to_dict(value):
    if hasattr(value, "__dataclass_fields__"):
        from dataclasses import asdict

        return asdict(value)

    return value