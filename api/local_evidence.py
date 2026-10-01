"""Private CPU-only bridge to recovered beta observations; no provider calls."""
from pathlib import Path
import hashlib
import math
import cv2
from core.vision_analyzer import analyze_intro_frames
from core.observers.temporal_evidence import build_temporal_evidence
from core.intelligence_v3 import build_intelligence_v3
from core.creator_report import build_creator_report


def analyze_owned_intro(path: Path, frame_directory: Path):
    capture = cv2.VideoCapture(str(path))
    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if not capture.isOpened() or not math.isfinite(fps) or not math.isfinite(count) or fps <= 0 or count <= 0 or min(width, height) <= 0:
            raise ValueError("Upload a readable video file.")
        if width * height > 3840 * 2160:
            raise ValueError("Use a video no larger than 3840 × 2160 pixels.")
        duration = min(count / fps, 10.0)
        frames, timestamps, sampled_indexes = [], [], set()
        frame_directory.mkdir(exist_ok=True)
        for index in range(20):
            requested = index * 0.5
            if requested >= duration:
                break
            target = int(round(requested * fps))
            if target in sampled_indexes:
                continue
            sampled_indexes.add(target)
            capture.set(cv2.CAP_PROP_POS_FRAMES, target)
            ok, frame = capture.read()
            if not ok:
                continue
            scale = min(1.0, 640 / max(frame.shape[:2]))
            if scale < 1:
                frame = cv2.resize(frame, (round(frame.shape[1] * scale), round(frame.shape[0] * scale)))
            output = frame_directory / f"frame_{index:03}.jpg"
            if cv2.imwrite(str(output), frame):
                frames.append(str(output))
                timestamps.append(target / fps)
    finally:
        capture.release()
    if not frames:
        raise ValueError("No intro frames could be decoded.")
    vision = analyze_intro_frames(frames, timestamps=timestamps)
    observations = vision.get("frame_observations", [])
    temporal = build_temporal_evidence(observations)
    intelligence = build_intelligence_v3(observations)
    source_context = {
        "source_type": "uploaded_file", "provenance": "user_supplied",
        "metadata_status": "unavailable", "benchmark_context_status": "unavailable",
    }
    report = {
        "status": "partial", "vision": vision, "temporal_evidence": temporal,
        "intelligence_v3": intelligence, "benchmark": {
            "status": "unavailable", "benchmark_quality": {"eligible_for_directional_learning": False}
        },
        "patterns": {}, "semantic_observation": {}, "creative_structure": {},
        "creative_understanding": {}, "source_context": source_context,
        "warnings": [
            "Only sampled frames from the first 10 seconds were observed; audio and retention were not measured.",
            "No qualified benchmark comparison or outcome evidence is available.",
        ],
    }
    creator = build_creator_report(report)
    # V4 intentionally presents at most one experiment. The recovered engine remains unchanged.
    if creator.get("experiments"):
        creator["experiments"] = creator["experiments"][:1]
    report["creator_report"] = creator
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "status": "partial", "evidence_level": "sampled_visual_observations",
        "engine_revision": "9721883370b5761767f519837a90af62e4122cd8",
        "asset_sha256": digest, "sample_count": len(observations), "intro_seconds": duration,
        "samples": [{key: frame.get(key) for key in (
            "timestamp", "brightness_score", "contrast_score", "motion_score",
        )} for frame in observations],
        "temporal_window_count": len(temporal.get("windows", [])),
        "change_event_count": len(intelligence.get("meaningful_change_events", [])),
        "report": report, "creator_report": creator,
        "recommendation": (creator.get("experiments") or [None])[0],
        "limitations": report["warnings"],
    }
