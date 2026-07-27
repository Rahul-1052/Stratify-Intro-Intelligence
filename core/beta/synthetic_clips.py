"""Deterministic, copyright-free synthetic clips for golden-dataset validation."""

import json
import math
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np


WIDTH = 640
HEIGHT = 360
FPS = 12
DURATION_SECONDS = 10
CASE_IDS = (
    "gd-001-static-talking-head",
    "gd-002-rapid-montage",
    "gd-003-early-subject",
    "gd-004-delayed-subject",
    "gd-005-early-text",
    "gd-006-late-text",
    "gd-007-frequent-scenes",
    "gd-008-no-scenes",
    "gd-009-stable-anchor",
    "gd-010-competing-focal",
)


def clip_filename(case_id):
    if case_id not in CASE_IDS:
        raise ValueError(f"Unsupported synthetic golden case: {case_id}")
    return f"{case_id}.mp4"


def validate_video(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size <= 0:
        return {"valid": False, "frame_count": 0, "fps": 0, "duration": 0}
    capture = cv2.VideoCapture(str(path))
    try:
        opened = capture.isOpened()
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        readable, _ = capture.read()
        duration = frame_count / fps if fps > 0 else 0
        return {
            "valid": bool(opened and readable and frame_count > 0 and fps > 0),
            "frame_count": frame_count, "fps": round(fps, 3),
            "duration": round(duration, 3), "width": width, "height": height,
            "size_bytes": path.stat().st_size,
        }
    finally:
        capture.release()


def _background(color):
    frame = np.empty((HEIGHT, WIDTH, 3), dtype=np.uint8)
    frame[:] = color
    return frame


def _subject(frame, center, scale=1.0, color=(70, 190, 245), phase=0.0):
    x, y = center
    radius = int(45 * scale)
    cv2.circle(frame, (x, y), radius, color, -1, cv2.LINE_AA)
    cv2.circle(frame, (x - radius // 3, y - radius // 5), 5, (30, 40, 50), -1)
    cv2.circle(frame, (x + radius // 3, y - radius // 5), 5, (30, 40, 50), -1)
    mouth = int(4 + 3 * abs(math.sin(phase)))
    cv2.ellipse(frame, (x, y + radius // 4), (15, mouth), 0, 0, 180,
                (30, 40, 50), 2, cv2.LINE_AA)
    cv2.ellipse(frame, (x, y + radius + int(55 * scale)),
                (int(75 * scale), int(70 * scale)), 0, 180, 360,
                color, -1, cv2.LINE_AA)


def _text(frame, value, position=(50, 85), scale=1.35):
    cv2.putText(frame, value, position, cv2.FONT_HERSHEY_DUPLEX, scale,
                (250, 250, 250), 3, cv2.LINE_AA)


def render_frame(case_id, frame_index, fps=FPS):
    time_seconds = frame_index / fps
    phase = frame_index * 0.22
    if case_id == CASE_IDS[0]:
        frame = _background((58, 78, 92))
        _subject(frame, (320 + int(3 * math.sin(phase / 5)), 145), phase=phase)
    elif case_id == CASE_IDS[1]:
        segment = int(time_seconds / 0.5)
        colors = ((35, 55, 190), (185, 55, 45), (40, 165, 85), (170, 70, 170))
        frame = _background(colors[segment % len(colors)])
        x = (80 + segment * 97) % 540
        cv2.rectangle(frame, (x, 45), (min(x + 130, 630), 300),
                      (240, 220, 50), -1)
        cv2.circle(frame, (WIDTH - x, 180), 45 + (segment % 3) * 18,
                   (35, 235, 235), -1, cv2.LINE_AA)
    elif case_id == CASE_IDS[2]:
        frame = _background((48, 92, 76))
        _subject(frame, (300, 145), phase=phase)
    elif case_id == CASE_IDS[3]:
        frame = _background((45, 52, 72))
        offset = int(25 * math.sin(phase / 4))
        cv2.circle(frame, (120 + offset, 180), 35, (100, 120, 155), 3)
        if time_seconds >= 3.5:
            _subject(frame, (390, 145), color=(80, 205, 245), phase=phase)
    elif case_id == CASE_IDS[4]:
        frame = _background((68, 72, 108))
        _subject(frame, (430, 160), scale=0.85, phase=phase)
        if time_seconds < 2.5:
            cv2.rectangle(frame, (25, 30), (370, 115), (30, 35, 58), -1)
            _text(frame, "START HERE", (45, 88), 1.15)
    elif case_id == CASE_IDS[5]:
        frame = _background((52, 102, 104))
        _subject(frame, (205, 155), scale=0.85, phase=phase)
        if time_seconds >= 4.5:
            cv2.rectangle(frame, (260, 90), (620, 175), (25, 50, 58), -1)
            _text(frame, "THE MAIN IDEA", (280, 145), 0.85)
    elif case_id == CASE_IDS[6]:
        segment = int(time_seconds)
        colors = ((35, 60, 120), (120, 45, 65), (35, 115, 85),
                  (130, 95, 35), (75, 45, 125))
        frame = _background(colors[segment % len(colors)])
        if segment % 3 == 0:
            _subject(frame, (180, 145), scale=0.75, phase=phase)
        elif segment % 3 == 1:
            cv2.rectangle(frame, (230, 55), (540, 300), (220, 180, 60), -1)
        else:
            cv2.circle(frame, (420, 170), 105, (70, 210, 220), -1)
    elif case_id == CASE_IDS[7]:
        frame = _background((66, 82, 88))
        _subject(frame, (320, 150), scale=0.9, color=(105, 185, 220), phase=0)
    elif case_id == CASE_IDS[8]:
        frame = _background((45, 58, 75))
        cv2.circle(frame, (320, 170), 75, (55, 205, 240), -1, cv2.LINE_AA)
        cv2.circle(frame, (320, 170), 30, (245, 245, 245), -1, cv2.LINE_AA)
        for index in range(5):
            x = int(320 + 180 * math.cos(phase / 9 + index * 1.25))
            y = int(170 + 120 * math.sin(phase / 11 + index * 1.25))
            cv2.circle(frame, (x, y), 12, (120, 105, 210), -1)
    elif case_id == CASE_IDS[9]:
        frame = _background((38, 48, 62))
        left_x = 185 + int(28 * math.sin(phase / 3))
        right_x = 455 + int(28 * math.cos(phase / 3))
        cv2.circle(frame, (left_x, 170), 82, (55, 190, 245), -1, cv2.LINE_AA)
        cv2.rectangle(frame, (right_x - 78, 92), (right_x + 78, 248),
                      (225, 85, 155), -1)
        cv2.circle(frame, (320, 170), 22 + int(8 * abs(math.sin(phase))),
                   (245, 235, 70), -1)
    else:
        raise ValueError(f"Unsupported synthetic golden case: {case_id}")
    return frame


def generate_clip(case_id, destination, force=False, fps=FPS,
                  duration=DURATION_SECONDS, size=(WIDTH, HEIGHT)):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force and validate_video(destination)["valid"]:
        return {"status": "skipped", **validate_video(destination)}
    writer = cv2.VideoWriter(
        str(destination), cv2.VideoWriter_fourcc(*"mp4v"), fps, size
    )
    if not writer.isOpened():
        raise RuntimeError(f"OpenCV could not open the MP4 writer for {destination}")
    try:
        for frame_index in range(int(fps * duration)):
            frame = render_frame(case_id, frame_index, fps)
            if size != (WIDTH, HEIGHT):
                frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
            writer.write(frame)
    finally:
        writer.release()
    validation = validate_video(destination)
    if not validation["valid"]:
        raise RuntimeError(f"Generated video failed validation: {destination}")
    return {"status": "generated", **validation}


def update_manifest(manifest_path, case_paths):
    manifest_path = Path(manifest_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    original_cases = payload.get("cases")
    if not isinstance(original_cases, list):
        raise ValueError("Manifest cases must be a list.")
    updated = 0
    for case in original_cases:
        case_id = case.get("case_id")
        if case_id in case_paths and case.get("local_clip_path") != case_paths[case_id]:
            case["local_clip_path"] = case_paths[case_id]
            updated += 1
    missing = set(case_paths).difference(
        case.get("case_id") for case in original_cases
    )
    if missing:
        raise ValueError(f"Manifest is missing synthetic cases: {', '.join(sorted(missing))}")
    if updated:
        fd, temporary = tempfile.mkstemp(
            prefix=".manifest-", suffix=".tmp", dir=manifest_path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temporary, manifest_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return updated


def generate_golden_clips(manifest_path, clips_dir=None, force=False,
                          generator=generate_clip):
    manifest_path = Path(manifest_path)
    clips_dir = Path(clips_dir or manifest_path.parent / "clips")
    clips_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    paths = {}
    for case_id in CASE_IDS:
        destination = clips_dir / clip_filename(case_id)
        results[case_id] = generator(case_id, destination, force=force)
        paths[case_id] = destination.relative_to(manifest_path.parent).as_posix()
    updated = update_manifest(manifest_path, paths)
    return {"results": results, "manifest_updated": updated, "clips_dir": clips_dir}
