from dataclasses import asdict, is_dataclass
from typing import Any, Dict

from core.feature_extractor import extract_video_features
from core.understanding import understand_video_intro
from core.vision_analyzer import analyze_intro_frames
from utils.frame_extractor import extract_frames_from_clip
from utils.video_downloader import download_video
from utils.video_utils import extract_intro_clip


def analyze_intro_pipeline(
    video: Dict[str, Any],
    url: str | None = None,
    intro_seconds: int = 15,
    frame_fps: int = 1,
) -> Dict[str, Any]:
    video_id = video.get("video_id")

    if not url:
        if not video_id:
            return _failure("normalize_url_failed", "Missing video id and URL.")
        url = f"https://www.youtube.com/watch?v={video_id}"

    download = download_video(url)
    if download.get("status") != "success":
        return _failure(
            download.get("error_type", "yt_dlp_download_failed"),
            download.get("message"),
        )

    clip = extract_intro_clip(
        download["video_path"],
        seconds=intro_seconds,
    )
    if clip.get("status") != "success":
        return _failure(
            clip.get("error_type", "intro_clip_failed"),
            clip.get("message"),
        )

    frames = extract_frames_from_clip(
        clip["clip_path"],
        fps=frame_fps,
    )
    if frames.get("status") != "success" or not frames.get("frames"):
        return _failure(
            frames.get("error_type", "frame_extract_failed"),
            frames.get("message"),
        )

    frame_paths = frames["frames"]

    vision = analyze_intro_frames(frame_paths)

    understanding_result = understand_video_intro(
        video_id=video_id or "",
        frame_observations=vision.get("frame_observations", []),
        intro_duration=float(intro_seconds),
        metadata=video,
    )

    understanding = _to_dict(understanding_result)

    features = extract_video_features(
        video,
        vision,
        frame_paths,
    )

    return {
        "status": "success",
        "video": video,
        "url": url,
        "frames": frame_paths,
        "vision": vision,
        "understanding": understanding,
        "features": features,
        "warnings": [],
    }


def _failure(stage: str, message: str | None) -> Dict[str, Any]:
    return {
        "status": "failed",
        "stage": stage,
        "error": message or "Unknown intro analysis error.",
        "warnings": [message or "Unknown intro analysis error."],
    }


def _to_dict(value):
    if is_dataclass(value):
        return asdict(value)
    return value