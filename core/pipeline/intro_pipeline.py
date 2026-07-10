from typing import Any, Dict

from core.acquisition import acquire_video_intro
from core.feature_extractor import extract_video_features
from core.understanding import build_intro_understanding
from core.vision_analyzer import analyze_intro_frames
from utils.frame_extractor import extract_frames_from_clip


def analyze_intro_pipeline(
    video: Dict[str, Any],
    url: str | None = None,
    intro_seconds: int = 15,
    frame_fps: int = 1,
) -> Dict[str, Any]:
    """
    Shared intro-analysis pipeline for user and benchmark videos.

    Flow:
    URL
    -> unified intro acquisition
    -> frame extraction
    -> visual observation
    -> intro understanding
    -> feature extraction
    """

    video_id = video.get("video_id")

    if not url:
        if not video_id:
            return _failure(
                stage="normalize_url_failed",
                message="Missing video id and URL.",
            )

        url = f"https://www.youtube.com/watch?v={video_id}"

    acquisition = acquire_video_intro(
        url=url,
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

    clip_path = acquisition.get("clip_path")

    if not clip_path:
        return _failure(
            stage="missing_intro_clip",
            message="Intro acquisition succeeded but returned no clip path.",
            attempts=acquisition.get("attempts", []),
        )

    frames = extract_frames_from_clip(
        clip_path,
        fps=frame_fps,
    )

    if frames.get("status") != "success" or not frames.get("frames"):
        return _failure(
            stage=frames.get("error_type", "frame_extract_failed"),
            message=frames.get(
                "message",
                "No frames were produced from the acquired intro clip.",
            ),
            attempts=acquisition.get("attempts", []),
        )

    frame_paths = frames["frames"]

    vision = analyze_intro_frames(frame_paths)

    understanding = build_intro_understanding(
        video=video,
        vision=vision,
        intro_duration=float(intro_seconds),
    )

    features = extract_video_features(
        video,
        vision,
        frame_paths,
    )

    return {
        "status": "success",
        "video": video,
        "url": acquisition.get("normalized_url", url),
        "clip_path": clip_path,
        "frames": frame_paths,
        "vision": vision,
        "understanding": understanding,
        "features": features,
        "acquisition": {
            "method": acquisition.get("method", "unknown"),
            "attempts": acquisition.get("attempts", []),
        },
        "warnings": acquisition.get("warnings", []),
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