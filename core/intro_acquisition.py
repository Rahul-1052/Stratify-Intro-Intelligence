from utils.frame_extractor import extract_frames_from_clip
from utils.video_downloader import download_video
from utils.video_utils import extract_intro_clip


def _warning_from_result(result, default_error_type, default_message):
    return (
        f"{result.get('error_type', default_error_type)}: "
        f"{result.get('message', default_message)}"
    )


def acquire_intro_evidence(url, intro_seconds=15, frame_fps=1):
    evidence = {
        "status": "failed",
        "method": "yt_dlp",
        "frames": [],
        "warnings": [],
        "error_reason": "",
        "evidence_completeness": "failed",
    }

    download_result = download_video(url)
    if download_result.get("status") != "success":
        warning = _warning_from_result(
            download_result,
            "yt_dlp_download_failed",
            "Unknown downloader error.",
        )
        evidence["warnings"].append(warning)
        evidence["error_reason"] = warning
        return evidence

    clip_result = extract_intro_clip(
        download_result["video_path"],
        seconds=intro_seconds,
    )
    if clip_result.get("status") != "success":
        warning = _warning_from_result(
            clip_result,
            "intro_clip_failed",
            "Unknown clip error.",
        )
        evidence["warnings"].append(warning)
        evidence["error_reason"] = warning
        return evidence

    frame_result = extract_frames_from_clip(
        clip_result["clip_path"],
        fps=frame_fps,
    )
    if frame_result.get("status") != "success" or not frame_result.get("frames"):
        warning = _warning_from_result(
            frame_result,
            "frame_extract_failed",
            "No frames were produced.",
        )
        evidence["warnings"].append(warning)
        evidence["error_reason"] = warning
        return evidence

    evidence["status"] = "success"
    evidence["frames"] = frame_result["frames"]
    evidence["evidence_completeness"] = "visual_complete"
    return evidence