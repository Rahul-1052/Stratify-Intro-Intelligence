import os
import math
from collections import Counter
from typing import Any, Dict, List

import cv2
import numpy as np
from dataclasses import dataclass


PROMINENT_FACE_AREA_RATIO = 0.2
DUPLICATE_FACE_OVERLAP_RATIO = 0.5


@dataclass(frozen=True)
class VisualCalibration:
    cut_score_threshold: float = 0.18
    text_score_threshold: float = 0.42
    prominent_region_min_ratio: float = 0.012
    competition_threshold: float = 0.52
    stable_centroid_drift: float = 0.08


VISUAL_CALIBRATION = VisualCalibration()


def analyze_intro_frames(frame_paths: List[str], timestamps=None) -> Dict[str, Any]:
    frame_paths = frame_paths or []
    observations = []

    previous_frame = None

    timestamps = list(timestamps or [])
    for index, frame_path in enumerate(frame_paths[:20]):
        frame = cv2.imread(frame_path)

        if frame is None:
            continue

        timestamp = float(timestamps[index]) if index < len(timestamps) else float(index)

        observation, previous_frame = _analyze_single_frame(
            frame=frame,
            frame_path=frame_path,
            timestamp=timestamp,
            previous_frame=previous_frame,
        )

        observations.append(observation)

    _smooth_text_presence(observations)
    summary = _summarize_observations(observations)

    return {
        "frame_count": len(frame_paths),
        "frames_analyzed": frame_paths[:20],
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
    previous_frame,
):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))

    dominant_lighting = _lighting_level(brightness)
    visual_clarity = _clarity_level(contrast)

    subject_count = _detect_human_count(frame)
    human_presence = subject_count > 0
    text_evidence = _text_region_evidence(gray)
    text_overlay = _detect_text_like_regions(gray)
    if text_overlay and not text_evidence["detected"]:
        text_evidence = {
            **text_evidence, "detected": True, "confidence": "limited",
        }
    scene_type = _infer_scene_type(human_presence, text_overlay)

    motion_score = 0.0
    if previous_frame is not None:
        previous_gray = cv2.cvtColor(previous_frame, cv2.COLOR_BGR2GRAY)
        motion_score = float(np.mean(cv2.absdiff(gray, previous_gray)))

    change = _visual_change_signals(frame, previous_frame)
    focal = _focal_structure(frame)

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
        "text_overlay_raw": text_overlay,
        "text_overlay_score": text_evidence["score"],
        "text_region_count": text_evidence["region_count"],
        "text_overlay_confidence": text_evidence["confidence"],
        "scene_type": scene_type,
        "brightness_score": round(brightness, 2),
        "contrast_score": round(contrast, 2),
        "motion_score": round(motion_score, 2),
        **change,
        **focal,
    }

    return observation, frame


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
    return _text_region_evidence(gray)["detected"]


def _text_region_evidence(gray):
    edges = cv2.Canny(gray, 70, 180)
    grouped = cv2.morphologyEx(
        edges, cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (13, 3)),
        iterations=1,
    )
    contours, _ = cv2.findContours(
        grouped, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    height, width = gray.shape
    regions, scores = [], []
    for contour in contours:
        x, y, region_width, region_height = cv2.boundingRect(contour)
        aspect = region_width / max(region_height, 1)
        if not (
            width * 0.09 <= region_width <= width * 0.88
            and 10 <= region_height <= height * 0.30
            and 2.0 <= aspect <= 18
        ):
            continue
        roi = edges[y:y + region_height, x:x + region_width]
        edge_density = float(np.count_nonzero(roi)) / max(roi.size, 1)
        if 0.025 <= edge_density <= 0.42:
            regions.append((x, y, region_width, region_height))
            size_score = min(1.0, region_width / (width * 0.35))
            density_score = min(1.0, edge_density / 0.12)
            scores.append(0.55 * size_score + 0.45 * density_score)
    score = round(max(scores, default=0.0), 3)
    detected = score >= VISUAL_CALIBRATION.text_score_threshold
    confidence = (
        "high" if score >= 0.72 else "moderate" if detected else "limited"
    )
    return {
        "detected": detected, "score": score,
        "region_count": len(regions), "confidence": confidence,
        "regions": regions,
    }


def _smooth_text_presence(observations):
    raw = [bool(item.get("text_overlay_raw")) for item in observations]
    for index, item in enumerate(observations):
        neighborhood = raw[max(0, index - 1):min(len(raw), index + 2)]
        persistent = raw[index] and (
            sum(neighborhood) >= 2
            or item.get("text_overlay_score", 0) >= 0.72
        )
        item["text_overlay"] = persistent
        item["text_temporal_support"] = sum(neighborhood)
        if raw[index] and not persistent:
            item["text_overlay_confidence"] = "limited"


def _visual_change_signals(frame, previous_frame):
    if previous_frame is None:
        return {
            "scene_cut_score": 0.0, "scene_cut_detected": False,
            "perceptual_novelty_score": 0.0,
            "cut_signal_components": {
                "frame_difference": 0.0, "histogram_distance": 0.0,
                "edge_layout_difference": 0.0, "luminance_shift": 0.0,
            },
        }
    current = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
    previous = cv2.resize(previous_frame, (160, 90), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(current, cv2.COLOR_BGR2GRAY)
    previous_gray = cv2.cvtColor(previous, cv2.COLOR_BGR2GRAY)
    frame_difference = float(np.mean(cv2.absdiff(current, previous))) / 255.0
    hist_current = cv2.calcHist([current], [0, 1], None, [16, 16], [0, 256, 0, 256])
    hist_previous = cv2.calcHist([previous], [0, 1], None, [16, 16], [0, 256, 0, 256])
    cv2.normalize(hist_current, hist_current)
    cv2.normalize(hist_previous, hist_previous)
    histogram_distance = float(
        cv2.compareHist(hist_current, hist_previous, cv2.HISTCMP_BHATTACHARYYA)
    )
    edges = cv2.Canny(gray, 70, 160)
    previous_edges = cv2.Canny(previous_gray, 70, 160)
    edge_layout = float(np.mean(cv2.absdiff(edges, previous_edges))) / 255.0
    luminance = abs(float(np.mean(gray)) - float(np.mean(previous_gray))) / 255.0
    cut_score = (
        0.38 * frame_difference + 0.32 * histogram_distance
        + 0.20 * edge_layout + 0.10 * luminance
    )
    novelty = min(1.0, cut_score / 0.42)
    return {
        "scene_cut_score": round(cut_score, 3),
        "scene_cut_detected": cut_score >= VISUAL_CALIBRATION.cut_score_threshold,
        "perceptual_novelty_score": round(novelty, 3),
        "cut_signal_components": {
            "frame_difference": round(frame_difference, 3),
            "histogram_distance": round(histogram_distance, 3),
            "edge_layout_difference": round(edge_layout, 3),
            "luminance_shift": round(luminance, 3),
        },
    }


def _focal_structure(frame):
    small = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
    blurred = cv2.GaussianBlur(small, (5, 5), 0)
    median_color = np.median(blurred.reshape(-1, 3), axis=0)
    distance = np.linalg.norm(
        blurred.astype(np.float32) - median_color.astype(np.float32), axis=2
    )
    threshold = max(28.0, float(np.percentile(distance, 76)))
    mask = (distance >= threshold).astype(np.uint8) * 255
    mask = cv2.morphologyEx(
        mask, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
    )
    mask = cv2.morphologyEx(
        mask, cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)),
    )
    count, _, stats, centroids = cv2.connectedComponentsWithStats(mask)
    frame_area = mask.size
    regions = []
    for index in range(1, count):
        area = int(stats[index, cv2.CC_STAT_AREA])
        ratio = area / frame_area
        if VISUAL_CALIBRATION.prominent_region_min_ratio <= ratio <= 0.48:
            regions.append({
                "area_ratio": ratio,
                "centroid": (
                    float(centroids[index][0]) / mask.shape[1],
                    float(centroids[index][1]) / mask.shape[0],
                ),
            })
    regions.sort(key=lambda item: item["area_ratio"], reverse=True)
    total = sum(item["area_ratio"] for item in regions)
    dominance = regions[0]["area_ratio"] / total if regions and total else 0.0
    competition = 0.0
    if len(regions) >= 2:
        ratio = regions[1]["area_ratio"] / max(regions[0]["area_ratio"], 1e-6)
        left, right = regions[0]["centroid"], regions[1]["centroid"]
        separation = math.dist(left, right) / math.sqrt(2)
        competition = ratio * min(1.0, separation / 0.25)
    focal = regions[0]["centroid"] if regions else None
    confidence = (
        "high" if regions and abs(competition - VISUAL_CALIBRATION.competition_threshold) >= 0.2
        else "moderate" if regions else "limited"
    )
    color_region_count = _prominent_color_regions(small)
    return {
        "prominent_region_count": max(len(regions), color_region_count),
        "focal_centroid": [round(value, 3) for value in focal] if focal else None,
        "focal_dominance_score": round(dominance, 3),
        "focal_competition_score": round(competition, 3),
        "focal_structure_confidence": confidence,
        "prominent_regions": [
            {"area_ratio": round(item["area_ratio"], 3),
             "centroid": [round(value, 3) for value in item["centroid"]]}
            for item in regions[:5]
        ],
    }


def _prominent_color_regions(frame):
    quantized = (frame.astype(np.uint16) // 48).reshape(-1, 3)
    _, counts = np.unique(quantized, axis=0, return_counts=True)
    if not len(counts):
        return 0
    largest = int(np.argmax(counts))
    total = frame.shape[0] * frame.shape[1]
    return int(sum(
        index != largest and total * 0.015 <= count <= total * 0.40
        for index, count in enumerate(counts)
    ))


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
