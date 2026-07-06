from core.feature_extractor import extract_video_features
from core.vision_analyzer import analyze_intro_frames
from utils.frame_extractor import extract_frames_from_clip
from utils.video_downloader import download_video
from utils.video_utils import extract_intro_clip


def _failure(video, stage, message):
    return {
        "video": video,
        "status": "failed",
        "stage": stage,
        "error": message or "Unknown error.",
    }


def extract_benchmark_features(videos, intro_seconds=15, frame_fps=1):
    results = []

    for video in videos or []:
        try:
            video_id = video.get("video_id")
            if not video_id:
                results.append(
                    _failure(video, "normalize_url_failed", "Missing video id.")
                )
                continue

            url = f"https://www.youtube.com/watch?v={video_id}"
            download = download_video(url)
            if download.get("status") != "success":
                results.append(
                    _failure(
                        video,
                        download.get("error_type", "yt_dlp_download_failed"),
                        download.get("message"),
                    )
                )
                continue

            clip = extract_intro_clip(
                download["video_path"],
                seconds=intro_seconds,
            )
            if clip.get("status") != "success":
                results.append(
                    _failure(
                        video,
                        clip.get("error_type", "intro_clip_failed"),
                        clip.get("message"),
                    )
                )
                continue

            frames = extract_frames_from_clip(
                clip["clip_path"],
                fps=frame_fps,
            )
            if frames.get("status") != "success" or not frames.get("frames"):
                results.append(
                    _failure(
                        video,
                        frames.get("error_type", "frame_extract_failed"),
                        frames.get("message"),
                    )
                )
                continue

            vision = analyze_intro_frames(frames["frames"])
            features = extract_video_features(
                video,
                vision,
                frames["frames"],
            )
            results.append(
                {
                    "video": video,
                    "status": "success",
                    "features": features,
                    "vision": vision,
                }
            )
        except Exception as exc:
            results.append(_failure(video, "unexpected", str(exc)))

    return results