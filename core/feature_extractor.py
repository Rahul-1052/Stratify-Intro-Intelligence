from core.vlm_feature_extractor import extract_intro_features


SUMMARY_FIELDS = (
    "frames_analyzed",
    "dominant_lighting",
    "dominant_color_feel",
    "human_presence",
    "text_overlay",
    "scene_type",
    "visual_energy",
    "motion_level",
    "scene_changes",
    "scene_change_count",
    "pacing_level",
    "first_frame_strength",
    "opening_action_type",
    "hook_visible_in_first_3_seconds",
    "subject_clarity",
    "conflict_visible",
    "payoff_teased",
    "curiosity_gap",
)


def extract_video_features(video, vision, frame_paths):
    intro_features = extract_intro_features(frame_paths)
    extracted = intro_features.get("features", {})
    feature_summary = {
        field: extracted.get(field, "unknown") for field in SUMMARY_FIELDS
    }

    return {
        "video_id": video.get("video_id"),
        "title": video.get("title"),
        "views": video.get("views", 0),
        "likes": video.get("likes", 0),
        "comments": video.get("comments", 0),
        "intro_features": intro_features,
        "feature_summary": feature_summary,
    }