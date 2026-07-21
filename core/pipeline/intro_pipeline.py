from pathlib import Path
from typing import Any, Dict

from core.acquisition import acquire_video_intro
from core.feature_extractor import extract_video_features
from core.understanding import build_intro_understanding, understand_creative_opening
from core.vision_analyzer import analyze_intro_frames
from core.observers.semantic_observer import observe_semantics
from utils.frame_extractor import extract_frames_from_clip
from utils.video_utils import extract_intro_clip


def analyze_intro_pipeline(
    video: Dict[str, Any],
    url: str | None = None,
    intro_seconds: int = 15,
    frame_fps: int = 1,
    local_video_path: str | None = None,
) -> Dict[str, Any]:
    """Analyze an intro from either YouTube or an uploaded local video."""

    source = _resolve_intro_source(
        video=video,
        url=url,
        local_video_path=local_video_path,
        intro_seconds=intro_seconds,
    )

    if source.get("status") != "success":
        return source

    clip_path = source.get("clip_path")
    if not clip_path:
        return _failure(
            stage="missing_intro_clip",
            message="Intro source succeeded but returned no clip path.",
            attempts=source.get("attempts", []),
            warnings=source.get("warnings", []),
        )

    frame_result = extract_frames_from_clip(clip_path, fps=frame_fps)
    if frame_result.get("status") != "success" or not frame_result.get("frames"):
        return _failure(
            stage=frame_result.get("error_type", "frame_extract_failed"),
            message=frame_result.get(
                "message",
                "No frames were produced from the acquired intro clip.",
            ),
            attempts=source.get("attempts", []),
            warnings=source.get("warnings", []),
        )

    frame_paths = frame_result["frames"]
    vision = analyze_intro_frames(frame_paths)
    semantic_observation = observe_semantics(
        vision.get("frame_observations", []),
        metadata_context={
            "title": video.get("title", ""),
            "description": video.get("description", ""),
            "channel_title": video.get("channel_title", ""),
        },
    )
    creative_structure, creative_understanding = understand_creative_opening(semantic_observation)

    understanding = build_intro_understanding(
        video=video,
        vision=vision,
        intro_duration=float(intro_seconds),
    )

    features = extract_video_features(video, vision, frame_paths)

    return {
        "status": "success",
        "video": video,
        "url": source.get("normalized_url", url or ""),
        "clip_path": clip_path,
        "frames": frame_paths,
        "vision": vision,
        "semantic_observation": semantic_observation,
        "creative_structure": creative_structure.to_dict(),
        "creative_understanding": creative_understanding.to_dict(),
        "understanding": understanding,
        "features": features,
        "acquisition": {
            "source": source.get("source", "unknown"),
            "method": source.get("method", "unknown"),
            "attempts": source.get("attempts", []),
        },
        "warnings": source.get("warnings", []),
    }


def _resolve_intro_source(
    video: Dict[str, Any],
    url: str | None,
    local_video_path: str | None,
    intro_seconds: int,
) -> Dict[str, Any]:
    if local_video_path:
        return _acquire_from_local_video(local_video_path, intro_seconds)

    resolved_url = url
    video_id = video.get("video_id")

    if not resolved_url:
        if not video_id:
            return _failure(
                stage="normalize_url_failed",
                message="Missing video id and URL.",
            )
        resolved_url = f"https://www.youtube.com/watch?v={video_id}"

    acquisition = acquire_video_intro(
        url=resolved_url,
        intro_seconds=intro_seconds,
    )

    if acquisition.get("status") != "success":
        return _failure(
            stage=acquisition.get("stage", "intro_acquisition_failed"),
            message=acquisition.get(
                "error",
                "Stratify could not acquire the video intro.",
            ),
            attempts=acquisition.get("attempts", []),
            warnings=acquisition.get("warnings", []),
        )

    return {
        "status": "success",
        "source": "youtube",
        "method": acquisition.get("method", "automatic_youtube_acquisition"),
        "normalized_url": acquisition.get("normalized_url", resolved_url),
        "clip_path": acquisition.get("clip_path", ""),
        "attempts": acquisition.get("attempts", []),
        "warnings": acquisition.get("warnings", []),
    }


def _acquire_from_local_video(
    local_video_path: str,
    intro_seconds: int,
) -> Dict[str, Any]:
    path = Path(local_video_path)

    if not path.exists() or not path.is_file():
        return _failure(
            stage="uploaded_video_missing",
            message="The uploaded video file could not be found.",
        )

    clip_result = extract_intro_clip(str(path), seconds=intro_seconds)
    if clip_result.get("status") != "success" or not clip_result.get("clip_path"):
        return _failure(
            stage=clip_result.get("error_type", "uploaded_intro_clip_failed"),
            message=clip_result.get(
                "message",
                "Stratify could not extract the intro from the uploaded video.",
            ),
        )

    return {
        "status": "success",
        "source": "uploaded_video",
        "method": "uploaded_video_local_clip",
        "normalized_url": "",
        "clip_path": clip_result["clip_path"],
        "attempts": [
            {
                "strategy": "uploaded_video_local_clip",
                "status": "success",
                "source_path": str(path),
            }
        ],
        "warnings": [],
    }


def _failure(
    stage: str,
    message: str | None,
    attempts: list | None = None,
    warnings: list | None = None,
) -> Dict[str, Any]:
    error_message = message or "Unknown intro analysis error."
    return {
        "status": "failed",
        "stage": stage,
        "error": error_message,
        "attempts": attempts or [],
        "warnings": warnings or [error_message],
    }
