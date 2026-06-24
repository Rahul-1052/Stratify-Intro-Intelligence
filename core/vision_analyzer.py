import os


def analyze_intro_frames(frame_paths):
    frame_count = len(frame_paths) if frame_paths else 0

    return {
        "frame_count": frame_count,
        "frames_analyzed": frame_paths[:10] if frame_paths else [],

        "emotion": "visual evidence collected",
        "visual_tone": "needs deeper visual interpretation",
        "story_setup": "Stratify extracted intro frames and is ready for deeper scene understanding.",
        "energy": "unknown until visual interpretation is added",
        "viewer_curiosity": "unknown until visual interpretation is added",

        "is_placeholder": True,
        "note": (
            "Intro frames were extracted successfully, but deep visual understanding "
            "has not been added yet. Stratify should not pretend to understand the intro."
        ),
    }