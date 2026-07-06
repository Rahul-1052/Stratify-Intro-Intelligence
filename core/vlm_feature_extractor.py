from pathlib import Path

import cv2
import numpy as np


def _safe_read_image(path):
    try:
        image = cv2.imread(str(path))
        if image is None:
            return None
        return image
    except Exception:
        return None


def _brightness_level(mean_brightness):
    if mean_brightness < 75:
        return "dark"
    if mean_brightness > 170:
        return "bright"
    return "medium"


def _color_feel(image):
    try:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        hue = hsv[:, :, 0]
        saturation = hsv[:, :, 1]

        valid = saturation > 40
        if valid.sum() == 0:
            return "neutral"

        avg_hue = float(hue[valid].mean())

        if avg_hue < 25 or avg_hue > 150:
            return "warm"
        if 80 <= avg_hue <= 140:
            return "cool"
        return "neutral"

    except Exception:
        return "unknown"


def _frame_difference(frame_a, frame_b):
    try:
        a = cv2.resize(frame_a, (160, 90))
        b = cv2.resize(frame_b, (160, 90))

        a_gray = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
        b_gray = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)

        diff = cv2.absdiff(a_gray, b_gray)
        return float(np.mean(diff))

    except Exception:
        return 0.0


def _motion_level(avg_difference):
    if avg_difference < 8:
        return "low"
    if avg_difference < 22:
        return "medium"
    return "high"


def _pacing_level(scene_change_count, frames_analyzed):
    if frames_analyzed <= 1:
        return "unknown"

    ratio = scene_change_count / max(frames_analyzed - 1, 1)

    if ratio < 0.20:
        return "slow"
    if ratio < 0.45:
        return "medium"
    return "fast"


def _visual_energy(motion_level, pacing_level):
    score = 0

    if motion_level == "medium":
        score += 1
    elif motion_level == "high":
        score += 2

    if pacing_level == "medium":
        score += 1
    elif pacing_level == "fast":
        score += 2

    if score <= 1:
        return "low"
    if score <= 3:
        return "medium"
    return "high"


def _detect_text_overlay(image):
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 80, 180)
        edge_density = float(np.mean(edges > 0))

        if edge_density > 0.13:
            return "present"
        if edge_density < 0.03:
            return "absent"
        return "unknown"

    except Exception:
        return "unknown"


def _detect_human_presence(image):
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)

        if face_cascade.empty():
            return "unknown"

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(40, 40),
        )

        if len(faces) > 0:
            return "present"

        return "unknown"

    except Exception:
        return "unknown"


def _scene_type_from_features(human_presence, text_overlay, motion_level, pacing_level):
    if human_presence == "present" and text_overlay == "present":
        return "reaction"

    if human_presence == "present" and motion_level in {"low", "medium"}:
        return "commentary"

    if motion_level == "high" and pacing_level == "fast":
        return "montage"

    if motion_level in {"medium", "high"} and human_presence == "unknown":
        return "movie_scene"

    return "unknown"


def _majority(values, default="unknown"):
    cleaned = [value for value in values if value and value != "unknown"]

    if not cleaned:
        return default

    counts = {}

    for value in cleaned:
        counts[value] = counts.get(value, 0) + 1

    return max(counts, key=counts.get)


def _edge_density(image):
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 80, 180)
        return float(np.mean(edges > 0))
    except Exception:
        return 0.0


def _contrast_score(image):
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return float(np.std(gray))
    except Exception:
        return 0.0


def _first_frame_strength(first_image):
    """
    Conservative estimate of whether the opening frame has immediate visual pull.
    """
    brightness = float(np.mean(cv2.cvtColor(first_image, cv2.COLOR_BGR2GRAY)))
    contrast = _contrast_score(first_image)
    edges = _edge_density(first_image)

    score = 0

    if 55 <= brightness <= 190:
        score += 1
    if contrast >= 45:
        score += 1
    if edges >= 0.06:
        score += 1

    if score >= 3:
        return "strong"
    if score == 2:
        return "moderate"
    return "weak"


def _subject_clarity(human_presence, motion_level, text_overlay, scene_type):
    """
    Estimates whether the intro gives viewers a clear subject quickly.
    """
    if human_presence == "present":
        return "clear"

    if text_overlay == "present" and motion_level in {"low", "medium"}:
        return "moderate"

    if scene_type in {"montage", "movie_scene"} and motion_level == "high":
        return "moderate"

    return "unclear"


def _opening_action_type(motion_level, pacing_level, scene_change_count):
    if motion_level == "high" and pacing_level == "fast":
        return "immediate_action"

    if scene_change_count >= 3:
        return "rapid_visual_setup"

    if motion_level == "medium":
        return "gradual_setup"

    if motion_level == "low":
        return "static_setup"

    return "unknown"


def _hook_visible_in_first_3_seconds(frame_differences, text_overlay, visual_energy):
    """
    Since frames are sampled around 1fps, first 3 differences roughly represent
    the first few seconds. This is not perfect, but it is measurable.
    """
    early_diffs = frame_differences[:3]

    if not early_diffs:
        if text_overlay == "present" or visual_energy == "high":
            return "likely"
        return "unknown"

    early_motion = float(np.mean(early_diffs))

    if early_motion >= 22 or text_overlay == "present":
        return "likely"

    if early_motion >= 10:
        return "possible"

    return "delayed_or_unclear"


def _conflict_visible(opening_action_type, visual_energy, scene_type):
    """
    Conservative proxy for visible tension/conflict.
    Does not claim narrative understanding.
    """
    if opening_action_type == "immediate_action" and visual_energy == "high":
        return "likely"

    if scene_type in {"montage", "movie_scene"} and visual_energy == "high":
        return "possible"

    return "unclear"


def _payoff_teased(first_frame_strength, visual_energy, text_overlay):
    if first_frame_strength == "strong" and visual_energy == "high":
        return "likely"

    if text_overlay == "present" or first_frame_strength == "moderate":
        return "possible"

    return "unclear"


def _curiosity_gap(subject_clarity, conflict_visible, payoff_teased):
    score = 0

    if subject_clarity in {"clear", "moderate"}:
        score += 1

    if conflict_visible in {"likely", "possible"}:
        score += 1

    if payoff_teased in {"likely", "possible"}:
        score += 1

    if score >= 3:
        return "strong"
    if score == 2:
        return "moderate"
    if score == 1:
        return "weak"
    return "unclear"


def extract_intro_features(frame_paths):
    """
    Intro Evidence V3.

    This extracts two kinds of evidence:

    1. Visual evidence:
       lighting, color, motion, pacing, text, human presence.

    2. Storytelling evidence:
       hook timing, first-frame strength, subject clarity, conflict visibility,
       payoff teaser, and curiosity gap.

    It does not call AI and does not invent values.
    """

    frame_paths = frame_paths or []
    images = []

    for path in frame_paths:
        image = _safe_read_image(Path(path))
        if image is not None:
            images.append(image)

    frames_analyzed = len(images)

    if frames_analyzed == 0:
        return {
            "status": "failed",
            "features": {
                "frames_analyzed": 0,
                "dominant_lighting": "unknown",
                "dominant_color_feel": "unknown",
                "motion_level": "unknown",
                "scene_changes": 0,
                "scene_change_count": 0,
                "pacing_level": "unknown",
                "visual_energy": "unknown",
                "human_presence": "unknown",
                "text_overlay": "unknown",
                "scene_type": "unknown",
                "first_frame_strength": "unknown",
                "opening_action_type": "unknown",
                "hook_visible_in_first_3_seconds": "unknown",
                "subject_clarity": "unknown",
                "conflict_visible": "unknown",
                "payoff_teased": "unknown",
                "curiosity_gap": "unknown",
            },
        }

    brightness_values = []
    color_values = []
    text_values = []
    human_values = []

    for image in images:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        brightness_values.append(float(np.mean(gray)))

        color_values.append(_color_feel(image))
        text_values.append(_detect_text_overlay(image))
        human_values.append(_detect_human_presence(image))

    avg_brightness = float(np.mean(brightness_values))
    dominant_lighting = _brightness_level(avg_brightness)
    dominant_color_feel = _majority(color_values)

    frame_differences = []

    for index in range(1, len(images)):
        frame_differences.append(
            _frame_difference(images[index - 1], images[index])
        )

    avg_difference = float(np.mean(frame_differences)) if frame_differences else 0.0
    motion_level = _motion_level(avg_difference)

    scene_change_count = len(
        [
            difference
            for difference in frame_differences
            if difference >= 25
        ]
    )

    pacing_level = _pacing_level(scene_change_count, frames_analyzed)
    visual_energy = _visual_energy(motion_level, pacing_level)

    human_presence = _majority(human_values)
    text_overlay = _majority(text_values)

    scene_type = _scene_type_from_features(
        human_presence,
        text_overlay,
        motion_level,
        pacing_level,
    )

    first_frame_strength = _first_frame_strength(images[0])

    opening_action_type = _opening_action_type(
        motion_level,
        pacing_level,
        scene_change_count,
    )

    hook_visible_in_first_3_seconds = _hook_visible_in_first_3_seconds(
        frame_differences,
        text_overlay,
        visual_energy,
    )

    subject_clarity = _subject_clarity(
        human_presence,
        motion_level,
        text_overlay,
        scene_type,
    )

    conflict_visible = _conflict_visible(
        opening_action_type,
        visual_energy,
        scene_type,
    )

    payoff_teased = _payoff_teased(
        first_frame_strength,
        visual_energy,
        text_overlay,
    )

    curiosity_gap = _curiosity_gap(
        subject_clarity,
        conflict_visible,
        payoff_teased,
    )

    return {
        "status": "success",
        "features": {
            "frames_analyzed": frames_analyzed,

            "dominant_lighting": dominant_lighting,
            "dominant_color_feel": dominant_color_feel,
            "motion_level": motion_level,
            "scene_changes": scene_change_count,
            "scene_change_count": scene_change_count,
            "pacing_level": pacing_level,
            "visual_energy": visual_energy,
            "human_presence": human_presence,
            "text_overlay": text_overlay,
            "scene_type": scene_type,

            "first_frame_strength": first_frame_strength,
            "opening_action_type": opening_action_type,
            "hook_visible_in_first_3_seconds": hook_visible_in_first_3_seconds,
            "subject_clarity": subject_clarity,
            "conflict_visible": conflict_visible,
            "payoff_teased": payoff_teased,
            "curiosity_gap": curiosity_gap,
        },
    }