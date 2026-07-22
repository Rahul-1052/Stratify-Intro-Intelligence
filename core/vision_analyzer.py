import os
from collections import Counter
from typing import Any, Dict, List

import cv2
import numpy as np


PROMINENT_FACE_AREA_RATIO = 0.2
DUPLICATE_FACE_OVERLAP_RATIO = 0.5


def analyze_intro_frames(frame_paths: List[str]) -> Dict[str, Any]:
    frame_paths = frame_paths or []
    observations = []

    previous_gray = None

    for index, frame_path in enumerate(frame_paths[:15]):
        frame = cv2.imread(frame_path)

        if frame is None:
            continue

        timestamp = float(index)

        observation, previous_gray = _analyze_single_frame(
            frame=frame,
            frame_path=frame_path,
            timestamp=timestamp,
            previous_gray=previous_gray,
        )

        observations.append(observation)

    summary = _summarize_observations(observations)

    return {
        "frame_count": len(frame_paths),
        "frames_analyzed": frame_paths[:15],
        "frame_observations": observations,
        **summary,
        "is_placeholder": False,
        "note": (
            "Intro frames were analyzed into timestamped visual observations. "
            "These are evidence signals, not final conclusions."
        ),
    }


def _analyze_single_frame(
    frame,
    frame_path: str,
    timestamp: float,
    previous_gray,
):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))

    dominant_lighting = _lighting_level(brightness)
    visual_clarity = _clarity_level(contrast)

    subject_count = _detect_human_count(frame)
    human_presence = subject_count > 0
    text_overlay = _detect_text_like_regions(gray)
    scene_type = _infer_scene_type(human_presence, text_overlay)

    motion_score = 0.0
    if previous_gray is not None:
        motion_score = float(np.mean(cv2.absdiff(gray, previous_gray)))

    visual_energy = _energy_level(motion_score, contrast)

    observation = {
        "timestamp": timestamp,
        "frame_path": frame_path,
        "dominant_lighting": dominant_lighting,
        "visual_clarity": visual_clarity,
        "visual_energy": visual_energy,
        "human_presence": human_presence,
        "subject_count": subject_count,
        "text_overlay": text_overlay,
        "text_overlay_confidence": "limited",
        "scene_type": scene_type,
        "brightness_score": round(brightness, 2),
        "contrast_score": round(contrast, 2),
        "motion_score": round(motion_score, 2),
    }

    return observation, gray


def _lighting_level(brightness: float) -> str:
    if brightness < 70:
        return "dark"
    if brightness > 175:
        return "bright"
    return "balanced"


def _clarity_level(contrast: float) -> str:
    if contrast >= 55:
        return "high"
    if contrast >= 35:
        return "moderate"
    return "low"


def _energy_level(motion_score: float, contrast: float) -> str:
    if motion_score >= 18 or contrast >= 65:
        return "high"
    if motion_score >= 7 or contrast >= 40:
        return "moderate"
    return "low"


def _detect_human_presence(frame) -> bool:
    return _detect_human_count(frame) > 0


def _detect_human_count(frame) -> int:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    if face_cascade.empty():
        return 0

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=4,
        minSize=(40, 40),
    )

    return _count_prominent_faces(faces)


def _count_prominent_faces(faces) -> int:
    boxes = [tuple(int(value) for value in face) for face in faces]
    if not boxes:
        return 0
    boxes.sort(key=lambda box: box[2] * box[3], reverse=True)
    distinct = []
    for box in boxes:
        x, y, width, height = box
        area = width * height
        duplicate = False
        for kept_x, kept_y, kept_width, kept_height in distinct:
            overlap_width = max(0, min(x + width, kept_x + kept_width) - max(x, kept_x))
            overlap_height = max(0, min(y + height, kept_y + kept_height) - max(y, kept_y))
            overlap = overlap_width * overlap_height
            if overlap / max(min(area, kept_width * kept_height), 1) >= DUPLICATE_FACE_OVERLAP_RATIO:
                duplicate = True
                break
        if not duplicate:
            distinct.append(box)
    largest_area = distinct[0][2] * distinct[0][3]
    return sum(
        width * height >= largest_area * PROMINENT_FACE_AREA_RATIO
        for _, _, width, height in distinct
    )


def _detect_text_like_regions(gray) -> bool:
    edges = cv2.Canny(gray, 100, 200)

    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    text_like_regions = 0

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)

        if 20 <= w <= 400 and 8 <= h <= 80:
            aspect_ratio = w / max(h, 1)

            if 1.5 <= aspect_ratio <= 12:
                text_like_regions += 1

    return text_like_regions >= 5


def _infer_scene_type(human_presence: bool, text_overlay: bool) -> str:
    if human_presence and text_overlay:
        return "person_with_text"
    if human_presence:
        return "person_focused"
    if text_overlay:
        return "text_or_graphic_focused"
    return "visual_scene"


def _summarize_observations(observations: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not observations:
        return {
            "dominant_lighting": "unknown",
            "visual_clarity": "unknown",
            "visual_energy": "unknown",
            "human_presence": False,
            "text_overlay": False,
            "scene_type": "unknown",
            "emotion": "unknown",
            "visual_tone": "unknown",
            "story_setup": "No usable visual observations were generated.",
            "energy": "unknown",
            "viewer_curiosity": "unknown",
        }

    return {
        "dominant_lighting": _majority(observations, "dominant_lighting"),
        "visual_clarity": _majority(observations, "visual_clarity"),
        "visual_energy": _majority(observations, "visual_energy"),
        "human_presence": any(obs.get("human_presence") for obs in observations),
        "text_overlay": any(obs.get("text_overlay") for obs in observations),
        "scene_type": _majority(observations, "scene_type"),
        "emotion": "visual evidence collected",
        "visual_tone": _majority(observations, "dominant_lighting"),
        "story_setup": (
            f"Stratify observed {len(observations)} intro frames and created "
            "timestamped evidence for visual structure, subject presence, text, "
            "motion, and clarity."
        ),
        "energy": _majority(observations, "visual_energy"),
        "viewer_curiosity": "requires benchmark and content comparison",
    }


def _majority(items: List[Dict[str, Any]], key: str) -> str:
    values = [item.get(key) for item in items if item.get(key) is not None]

    if not values:
        return "unknown"

    return Counter(values).most_common(1)[0][0]
