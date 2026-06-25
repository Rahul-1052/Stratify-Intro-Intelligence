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
from core.intro_acquisition import acquire_intro_evidence

from utils.video_downloader import download_video
from utils.video_utils import extract_intro_clip
from utils.frame_extractor import extract_frames_from_clip


def run_stratify_report(url, intro_seconds=8, frame_fps=1, progress_callback=None):
    warnings = []

    def progress(message):
        if progress_callback:
            progress_callback(message)

    try:
        progress("🧠 Understanding your creative identity...")
        data = get_full_youtube_context(url)

        if data is None:
            return {
                "status": "failed",
                "warnings": ["Could not fetch video data from YouTube."],
            }

        video = data["video"]
        channel = data["channel"]
        recent_videos = data["recent_videos"]
	
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
	category = {}
	benchmark = {}
        feature_report = {}

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
                    feature_report = extract_video_features(video, vision, frames)

                    progress("🎭 Understanding the scene...")
                    scene = understand_scene(vision)

                    progress("🌎 Understanding the world around your content...")
                    context = get_context_intelligence(video, channel)

                    progress("❤️ Discovering why audiences care...")
                    emotion = detect_emotional_center(video, context, vision)

                    progress("🚀 Building your growth report...")
                    brain = generate_creator_insights(vision, context, emotion)
                    big = generate_big_insight(emotion, context, scene)
                    meaning = generate_content_meaning(video, emotion, context)
                else:
                    warnings.append(f"Frame extraction failed: {frame_result.get('message', 'Unknown error')}")
            else:
                warnings.append(f"Intro clip extraction failed: {clip_result.get('message', 'Unknown error')}")
        else:
            warnings.append(f"Video download failed: {download_result.get('message', 'Unknown error')}")

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
            "brain": brain,
            "big_insight": big,
            "meaning": meaning,
            "feature_report": feature_report,
        }

    except Exception as e:
        return {
            "status": "failed",
            "warnings": [str(e)],
        }
