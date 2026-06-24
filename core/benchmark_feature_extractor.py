from utils.video_downloader import download_video
from utils.video_utils import extract_intro_clip
from utils.frame_extractor import extract_frames_from_clip

from core.vision_analyzer import analyze_intro_frames
from core.feature_extractor import extract_video_features


def extract_benchmark_features(videos):

    results = []

    for video in videos:

        try:

            url = f"https://www.youtube.com/watch?v={video['video_id']}"

            download = download_video(url)

            if download.get("status") != "success":
                continue

            clip = extract_intro_clip(
                download["video_path"],
                seconds=8,
            )

            if clip.get("status") != "success":
                continue

            frames = extract_frames_from_clip(
                clip["clip_path"],
                fps=1,
            )

            if frames.get("status") != "success":
                continue

            vision = analyze_intro_frames(
                frames["frames"]
            )

            features = extract_video_features(
                video,
                vision,
                frames["frames"]
            )

            results.append({

                "video": video,

                "features": features,

                "vision": vision

            })

        except Exception as e:
            results.append({
                "video": video,
                "status": "failed",
                "error": str(e),
            })

    return results