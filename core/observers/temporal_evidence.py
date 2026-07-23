"""Typed deterministic evidence aggregated before semantic interpretation."""

from dataclasses import asdict, dataclass, field
from typing import List, Mapping


@dataclass
class TemporalEvidenceWindow:
    evidence_type: str
    start_time: float
    end_time: float
    duration: float
    supporting_samples: int
    total_samples: int
    persistence: str
    confidence: str
    confidence_reasons: List[str] = field(default_factory=list)
    contradictions: List[int] = field(default_factory=list)
    source_observations: List[int] = field(default_factory=list)


def _window(kind, frames, indexes, confidence="moderate", reasons=None):
    timestamps = [float(frames[index].get("timestamp", index)) for index in indexes]
    step = min([b - a for a, b in zip(timestamps, timestamps[1:]) if b > a] or [1.0])
    support, total = len(indexes), len(frames)
    persistence = "isolated" if support == 1 else "persistent" if support / total >= 0.6 else "recurring"
    return TemporalEvidenceWindow(
        kind, timestamps[0], timestamps[-1] + step, round(timestamps[-1] - timestamps[0] + step, 3),
        support, total, persistence, confidence, list(reasons or []),
        [i for i in range(total) if i not in indexes], indexes,
    )


def build_temporal_evidence(frame_observations):
    frames = [dict(item) for item in frame_observations or [] if isinstance(item, Mapping)]
    frames.sort(key=lambda item: float(item.get("timestamp", 0)))
    windows, rejected = [], []
    specifications = (
        ("text_like", lambda f: f.get("text_overlay") is True),
        ("subject_presence", lambda f: f.get("human_presence") is True),
        ("multiple_subjects", lambda f: int(f.get("subject_count") or 0) >= 2),
    )
    for kind, predicate in specifications:
        indexes = [i for i, frame in enumerate(frames) if predicate(frame)]
        if not indexes:
            continue
        limited = kind == "text_like" and any(str(frames[i].get("text_overlay_confidence", "")).lower() == "limited" for i in indexes)
        reasons = [f"{kind.replace('_', ' ').title()} evidence appears across {len(indexes)} sampled timestamp(s)."]
        if limited:
            reasons.append("The contour detector cannot verify readable text.")
        window = _window(kind, frames, indexes, "limited" if limited else "moderate", reasons)
        if window.persistence == "isolated" and kind in {"text_like", "multiple_subjects"}:
            rejected.append({"evidence_type": kind, "sample": indexes[0], "reason": "isolated_detection"})
        windows.append(window)
    active = [i for i, frame in enumerate(frames) if float(frame.get("motion_score") or 0) >= 7]
    if active:
        window = _window("transition_activity", frames, active, reasons=["Adjacent sampled frames show measurable appearance change."])
        window.persistence = "rapid" if len(active) / len(frames) >= 0.6 else "clear" if len(active) > 1 else "uncertain"
        windows.append(window)
    return {
        "version": "temporal-evidence-v2", "sample_count": len(frames),
        "windows": [asdict(item) for item in windows], "rejected_isolated_evidence": rejected,
        "confidence_reasons": ["Evidence is aggregated across explicit sample timestamps."] if frames else ["No frame observations were available."],
    }
