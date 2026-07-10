from typing import Any, Dict

from core.acquisition.youtube_acquisition import acquire_intro_clip as acquire_section
from utils.video_downloader import download_video, normalize_youtube_url
from utils.video_utils import extract_intro_clip


def acquire_video_intro(
    url: str,
    intro_seconds: int = 15,
) -> Dict[str, Any]:
    """
    Single entry point for acquiring a YouTube intro clip.

    Strategy:
    1. Download only the requested intro section.
    2. If that fails, download the full video.
    3. Extract the intro locally from the full download.
    """

    attempts = []

    try:
        normalized_url = normalize_youtube_url(url)
    except ValueError as exc:
        return _failure(
            stage="normalize_url_failed",
            message=str(exc),
            attempts=attempts,
        )

    section_result = acquire_section(
        normalized_url,
        intro_seconds=intro_seconds,
    )

    attempts.append({
        "strategy": "direct_intro_section",
        "status": section_result.get("status", "failed"),
        "method": section_result.get("method", ""),
        "warnings": section_result.get("warnings", []),
    })

    if (
        section_result.get("status") == "success"
        and section_result.get("clip_path")
    ):
        return {
            "status": "success",
            "clip_path": section_result["clip_path"],
            "method": section_result.get("method", "direct_intro_section"),
            "normalized_url": normalized_url,
            "attempts": attempts,
            "warnings": section_result.get("warnings", []),
        }

    full_download = download_video(normalized_url)

    attempts.append({
        "strategy": "full_video_download",
        "status": full_download.get("status", "error"),
        "method": full_download.get("download_strategy", ""),
        "message": full_download.get("message", ""),
        "details": full_download.get("attempts", ""),
    })

    if full_download.get("status") != "success":
        return _failure(
            stage=full_download.get("error_type", "full_download_failed"),
            message=full_download.get(
                "message",
                "Could not download the YouTube video.",
            ),
            attempts=attempts,
        )

    clip_result = extract_intro_clip(
        full_download["video_path"],
        seconds=intro_seconds,
    )

    attempts.append({
        "strategy": "local_intro_extraction",
        "status": clip_result.get("status", "failed"),
        "message": clip_result.get("message", ""),
    })

    if (
        clip_result.get("status") != "success"
        or not clip_result.get("clip_path")
    ):
        return _failure(
            stage=clip_result.get("error_type", "intro_clip_failed"),
            message=clip_result.get(
                "message",
                "The intro could not be extracted from the downloaded video.",
            ),
            attempts=attempts,
        )

    return {
        "status": "success",
        "clip_path": clip_result["clip_path"],
        "method": (
            f"full_download_fallback:"
            f"{full_download.get('download_strategy', 'unknown')}"
        ),
        "normalized_url": normalized_url,
        "attempts": attempts,
        "warnings": [],
    }


def _failure(
    stage: str,
    message: str,
    attempts: list,
) -> Dict[str, Any]:
    return {
        "status": "failed",
        "stage": stage,
        "error": message or "Unknown acquisition error.",
        "clip_path": "",
        "method": "",
        "attempts": attempts,
        "warnings": [message or "Unknown acquisition error."],
    }