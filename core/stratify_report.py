from core.youtube_client import get_full_youtube_context

from core.content_dna import generate_content_dna
from core.growth_snapshot import generate_growth_snapshot

from core.vision_analyzer import analyze_intro_frames
from core.scene_understanding import understand_scene

from core.context_intelligence import get_context_intelligence
from core.emotional_center import detect_emotional_center

from core.stratify_brain import generate_creator_insights
from core.big_insight import generate_big_insight
from core.meaning_engine import generate_content_meaning

from core.feature_extractor import extract_video_features
from core.category_intelligence import understand_category
from core.benchmark_collector import collect_benchmark_videos
from core.benchmark_feature_extractor import extract_benchmark_features
from core.pattern_discovery import discover_patterns

from utils.video_downloader import download_video
from utils.video_utils import extract_intro_clip
from utils.frame_extractor import extract_frames_from_clip


def run_stratify_report(url, intro_seconds=8, frame_fps=1, progress_callback=None):
    warnings = []

    def progress(message):
        if progress_callback:
            progress_callback(message)

    try:
        progress("🧠 Understanding video context...")
        data = get_full_youtube_context(url)

        if data is None:
            return {
                "status": "failed",
                "warnings": ["Could not fetch video data from YouTube."],
            }

        video = data["video"]
        channel = data["channel"]
        recent_videos = data["recent_videos"]

        progress("🔎 Discovering benchmark context...")
        category = understand_category(video)

        benchmark = collect_benchmark_videos(
            category,
            user_video_id=video.get("video_id"),
            max_results=15,
        )

        vision = {}
        feature_report = {}
        benchmark_features = {
            "top_performers": [],
            "lower_performers": [],
        }
        patterns = {}

        # -------------------------------------------------
        # USER INTRO EVIDENCE
        # -------------------------------------------------

        progress("🎬 Watching your intro...")
        download_result = download_video(url)

        if download_result.get("status") == "success":
            clip_result = extract_intro_clip(
                download_result["video_path"],
                seconds=intro_seconds,
            )

            if clip_result.get("status") == "success":
                frame_result = extract_frames_from_clip(
                    clip_result["clip_path"],
                    fps=frame_fps,
                )

                if frame_result.get("status") == "success":
                    progress("👀 Extracting intro evidence...")
                    frames = frame_result["frames"]

                    vision = analyze_intro_frames(frames)

                    feature_report = extract_video_features(
                        video,
                        vision,
                        frames,
                    )
                else:
                    warnings.append("Frame extraction failed for the user video.")
            else:
                warnings.append("Intro extraction failed for the user video.")
        else:
            warnings.append(
                "Video download failed for the user video: "
                f"{download_result.get('message', 'Unknown downloader error.')}"
            )

        # -------------------------------------------------
        # BENCHMARK INTRO EVIDENCE
        # This must run even if the user intro fails.
        # -------------------------------------------------

        progress("🏆 Watching benchmark intros...")
        benchmark_features = {
            "top_performers": extract_benchmark_features(
                benchmark.get("top_performers", [])[:3]
            ),
            "lower_performers": extract_benchmark_features(
                benchmark.get("lower_performers", [])[:3]
            ),
        }

        # -------------------------------------------------
        # PATTERN DISCOVERY
        # Only compare user position if user evidence exists.
        # -------------------------------------------------

        progress("🧩 Discovering evidence-based patterns...")
        patterns = discover_patterns(
            benchmark_features.get("top_performers", []),
            benchmark_features.get("lower_performers", []),
            feature_report,
        )

        return {
            "status": "partial" if warnings else "success",
            "warnings": warnings,
            "video": video,
            "channel": channel,
            "recent_videos": recent_videos,
            "category": category,
            "benchmark": benchmark,
            "benchmark_features": benchmark_features,
            "patterns": patterns,
            "feature_report": feature_report,
            "vision": vision,

            # Old narrative sections kept disabled in UI for Stratify 2.0 evidence-first mode
            "scene": {},
            "context": {},
            "emotion": {},
            "brain": {},
            "big_insight": {},
            "meaning": {},
            "content_dna": {},
            "growth_snapshot": {},
        }

    except Exception as e:
        return {
            "status": "failed",
            "warnings": [f"Unexpected Stratify error: {str(e)}"],
        }