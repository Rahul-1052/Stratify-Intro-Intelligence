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

        # OpenCV hue range is 0-179
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
    """
    Conservative text-overlay heuristic.

    This does NOT use OCR.
    It only detects strong rectangular/edge-heavy overlay-like regions.
    If uncertain, returns unknown.
    """

    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        edges = cv2.Canny(gray, 80, 180)
        edge_density = float(np.mean(edges > 0))

        # Text overlays often produce dense sharp edges.
        if edge_density > 0.13:
            return "present"

        if edge_density < 0.03:
            return "absent"

        return "unknown"

    except Exception:
        return "unknown"


def _detect_human_presence(image):
    """
    Conservative person/face detection.

    Uses OpenCV Haar face detector if available.
    If not confident, returns unknown.
    """

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
    """
    Conservative scene type classification.

    This is intentionally simple.
    If evidence is not strong, return unknown.
    """

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


def extract_intro_features(frame_paths):
    """
    Intro Evidence V2.

    Input:
        frame_paths: list of frame image paths

    Output:
        {
            "status": "success",
            "features": {...}
        }

    This function is evidence-first:
    - It measures what can be measured.
    - It returns "unknown" when evidence is weak.
    - It does not use fake psychology.
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
                "pacing_level": "unknown",
                "visual_energy": "unknown",
                "human_presence": "unknown",
                "text_overlay": "unknown",
                "scene_type": "unknown",
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
        },
    }