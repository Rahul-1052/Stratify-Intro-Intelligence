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
from core.category_detector import detect_video_category
from core.benchmark_collector import collect_benchmark_videos
from core.benchmark_feature_extractor import extract_benchmark_features
from core.pattern_discovery import discover_patterns
from core.intro_acquisition import acquire_intro_evidence
from core.intro_observer import observe_intro


def run_stratify_report(url, intro_seconds=15, frame_fps=1, progress_callback=None):
    warnings = []

    def progress(message):
        if progress_callback:
            progress_callback(message)

    try:
        progress("Understanding video context...")
        data = get_full_youtube_context(url)

        if data is None:
            return {
                "status": "failed",
                "warnings": ["Could not fetch video data from YouTube."],
            }

        video = data["video"]
        channel = data["channel"]
        recent_videos = data["recent_videos"]

        progress("Discovering benchmark context...")
        category = detect_video_category(video)

        benchmark = collect_benchmark_videos(
            category,
            user_video_id=video.get("video_id"),
            max_results=15,
        )

        dna = generate_content_dna(video, channel, recent_videos)
        snapshot = generate_growth_snapshot(video, channel, recent_videos)

        vision = {}
        scene = {}
        context = {}
        emotion = {}
        brain = {}
        big = {}
        meaning = {}
        feature_report = {}
        intro_observation = {}

        benchmark_features = {
            "top_performers": [],
            "lower_performers": [],
        }

        patterns = {}

        progress("Watching your intro...")
        intro_evidence = acquire_intro_evidence(
            url,
            intro_seconds=intro_seconds,
            frame_fps=frame_fps,
        )

        if intro_evidence.get("status") == "success" and intro_evidence.get("frames"):
            progress("Extracting intro evidence...")
            frames = intro_evidence["frames"]

            progress("Observing intro with local VLM...")
            intro_observation = observe_intro(frames)

            vision = analyze_intro_frames(frames)
            feature_report = extract_video_features(video, vision, frames)

            progress("Understanding the scene...")
            scene = understand_scene(vision)

            progress("Understanding the world around your content...")
            context = get_context_intelligence(video, channel)

            progress("Discovering why audiences care...")
            emotion = detect_emotional_center(video, context, vision)

            progress("Building your growth report...")
            brain = generate_creator_insights(vision, context, emotion)
            big = generate_big_insight(emotion, context, scene)
            meaning = generate_content_meaning(video, emotion, context)
        else:
            warnings.extend(intro_evidence.get("warnings", []))

        progress("Watching benchmark intros...")
        benchmark_features = {
            "top_performers": extract_benchmark_features(
                benchmark.get("top_performers", [])[:3]
            ),
            "lower_performers": extract_benchmark_features(
                benchmark.get("lower_performers", [])[:3]
            ),
        }

        if not benchmark_features["top_performers"]:
            warnings.append("No top performers intros could be analyzed.")

        if not benchmark_features["lower_performers"]:
            warnings.append("No lower performers intros could be analyzed.")

        progress("Comparing observed intro patterns...")
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
            "content_dna": dna,
            "growth_snapshot": snapshot,
            "vision": vision,
            "scene": scene,
            "context": context,
            "emotion": emotion,
            "category": category,
            "benchmark": benchmark,
            "benchmark_features": benchmark_features,
            "patterns": patterns,
            "brain": brain,
            "big_insight": big,
            "meaning": meaning,
            "feature_report": feature_report,
            "intro_observation": intro_observation,
        }

    except Exception as e:
        return {
            "status": "failed",
            "warnings": [f"Unexpected Stratify error: {str(e)}"],
        }