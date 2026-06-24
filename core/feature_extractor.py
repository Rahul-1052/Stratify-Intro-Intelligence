from core.vlm_feature_extractor import extract_intro_features


def extract_video_features(video, vision, frame_paths):
    intro_features = extract_intro_features(frame_paths)
    features = intro_features.get("features", {})

    return {
        "video_id": video.get("video_id"),
        "title": video.get("title"),
        "views": video.get("views", 0),
        "likes": video.get("likes", 0),
        "comments": video.get("comments", 0),

        "intro_features": intro_features,

        "feature_summary": {
            "frames_analyzed": features.get("frames_analyzed", 0),
            "dominant_lighting": features.get("dominant_lighting", "unknown"),
            "dominant_color_feel": features.get("dominant_color_feel", "unknown"),
            "human_presence": features.get("human_presence", "unknown"),
            "text_overlay": features.get("text_overlay", "unknown"),
            "scene_type": features.get("scene_type", "unknown"),
            "visual_energy": features.get("visual_energy", "unknown"),
            "motion_level": features.get("motion_level", "unknown"),
            "scene_changes": features.get(
                "scene_changes",
                features.get("scene_change_count", "unknown"),
            ),
            "scene_change_count": features.get(
                "scene_change_count",
                features.get("scene_changes", "unknown"),
            ),
            "pacing_level": features.get("pacing_level", "unknown"),
        },
    }