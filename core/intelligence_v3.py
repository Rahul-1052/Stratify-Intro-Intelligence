"""CPU-only, typed temporal evidence for evidence-driven creator intelligence."""

from dataclasses import asdict, dataclass, field
from statistics import median
import math
from typing import Any, Dict, List, Mapping


AVAILABILITY_STATES = {
    "unavailable", "available_but_weak", "available_and_qualified",
    "conflicting", "not_applicable",
}
CONFIDENCE_LEVELS = {"limited", "moderate", "high"}


@dataclass
class EvidenceFinding:
    finding_id: str
    observation_type: str
    start_time: float
    end_time: float
    measured_value: Any
    comparison_value: Any = None
    evidence_strength: str = "limited"
    evidence_source: str = "sampled_video_frames"
    supporting_observations: List[Dict[str, Any]] = field(default_factory=list)
    conflicting_observations: List[Dict[str, Any]] = field(default_factory=list)
    availability_state: str = "unavailable"
    qualification_result: str = "not_qualified"
    limitations: List[str] = field(default_factory=list)
    provenance: str = "deterministic_local_measurement"

    def __post_init__(self):
        if self.availability_state not in AVAILABILITY_STATES:
            raise ValueError(f"Unsupported availability state: {self.availability_state}")
        if self.evidence_strength not in CONFIDENCE_LEVELS:
            raise ValueError(f"Unsupported evidence strength: {self.evidence_strength}")

    def to_dict(self):
        return asdict(self)


@dataclass
class MeaningfulChangeEvent:
    timestamp: float
    event_type: str
    previous_state: Any
    new_state: Any
    evidence_strength: str
    supporting_measurements: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    novelty_score: float = 0.0

    def to_dict(self):
        return asdict(self)


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _state(frame):
    subject_count = int(_number(
        frame.get("subject_count", frame.get("person_count", frame.get("face_count", 0)))
    ))
    return {
        "composition": str(frame.get("composition_state") or frame.get("composition")
                           or frame.get("scene_type") or "unavailable"),
        "scene": str(frame.get("scene_type") or "unavailable"),
        "subject_count": subject_count,
        "subject_present": bool(frame.get("human_presence")) or subject_count > 0,
        "dominant_subject": str(frame.get("dominant_focus") or
                                ("visible_subject" if subject_count else "no_visible_subject")),
        "text": bool(frame.get("text_overlay")),
        "motion": str(frame.get("motion_state") or (
            "active" if _number(frame.get("motion_score")) >= 7 else "held"
        )),
        "lighting": str(frame.get("dominant_lighting") or "unavailable"),
        "brightness": _number(frame.get("brightness_score")),
        "contrast": _number(frame.get("contrast_score")),
        "energy": str(frame.get("visual_energy") or "unavailable"),
        "focal_region": str(frame.get("dominant_focal_region") or
                            frame.get("dominant_focus") or "unavailable"),
        "graphic_regions": int(_number(frame.get("graphic_region_count"))),
    }


def _meaningful_differences(previous, current):
    differences = []
    categorical = (
        ("composition_change", "composition"),
        ("scene_change", "scene"),
        ("subject_count_change", "subject_count"),
        ("dominant_subject_change", "dominant_subject"),
        ("text_overlay_change", "text"),
        ("motion_state_change", "motion"),
        ("focal_region_change", "focal_region"),
        ("visual_energy_change", "energy"),
    )
    for event_type, key in categorical:
        before, after = previous[key], current[key]
        if before != after and "unavailable" not in {before, after}:
            differences.append((event_type, key, before, after))
    brightness_delta = abs(current["brightness"] - previous["brightness"])
    if previous["lighting"] != current["lighting"] and brightness_delta >= 18:
        differences.append(("lighting_change", "lighting", previous["lighting"], current["lighting"]))
    return differences


def _events(frames):
    events = []
    for index in range(1, len(frames)):
        previous, current = _state(frames[index - 1]), _state(frames[index])
        differences = _meaningful_differences(previous, current)
        if frames[index].get("scene_cut_detected") and not any(
            item[0] == "scene_change" for item in differences
        ):
            differences.append((
                "scene_change", "perceptual_scene_cut",
                "previous_visual_state", "new_visual_state",
            ))
        if not differences:
            continue
        timestamp = _number(frames[index].get("timestamp"), index)
        perceptual_novelty = _number(
            frames[index].get("perceptual_novelty_score")
        )
        novelty = max(
            perceptual_novelty,
            min(1.0, len({item[1] for item in differences}) / 5.0),
        )
        for event_type, key, before, after in differences:
            warnings = []
            strength = "moderate"
            if event_type == "text_overlay_change":
                warnings.append("Text-like regions are detected visually; readability is not verified.")
                strength = "limited"
            events.append(MeaningfulChangeEvent(
                timestamp=timestamp, event_type=event_type,
                previous_state=before, new_state=after, evidence_strength=strength,
                supporting_measurements={
                    "changed_dimension": key,
                    "motion_score": _number(frames[index].get("motion_score")),
                    "brightness_delta": round(
                        abs(current["brightness"] - previous["brightness"]), 3
                    ),
                    "sample_before": index - 1, "sample_after": index,
                    "scene_cut_score": _number(
                        frames[index].get("scene_cut_score")
                    ),
                },
                warnings=warnings, novelty_score=round(novelty, 3),
            ))
    return events


def _stable_intervals(frames, events):
    if not frames:
        return []
    timestamps = [_number(frame.get("timestamp"), index) for index, frame in enumerate(frames)]
    boundaries = sorted({timestamps[0], *[event.timestamp for event in events], timestamps[-1]})
    if len(boundaries) == 1:
        return [{"start_time": boundaries[0], "end_time": boundaries[0],
                 "duration": 0.0}]
    return [
        {"start_time": start, "end_time": end, "duration": round(end - start, 3)}
        for start, end in zip(boundaries, boundaries[1:])
    ]


def _progression(intervals):
    if len(intervals) < 3:
        return "insufficient_evidence"
    first = median(intervals[:max(1, len(intervals) // 2)])
    last = median(intervals[len(intervals) // 2:])
    tolerance = max(0.15, median(intervals) * 0.2)
    if abs(first - last) <= tolerance:
        spread = max(intervals) - min(intervals)
        return "stable" if spread <= max(0.25, median(intervals) * 0.35) else "irregular"
    return "accelerating" if last < first else "decelerating"


def _subject_continuity(frames):
    if len(frames) < 2:
        return "insufficient_evidence"
    states = [_state(frame)["subject_count"] for frame in frames]
    present = [value > 0 for value in states]
    if not any(present):
        return "no_reliable_visible_subject"
    if all(present) and len(set(states)) == 1:
        return "stable_visible_subject"
    if not present[0] and any(present[1:]):
        return "subject_introduced_later"
    transitions = sum(left != right for left, right in zip(states, states[1:]))
    if transitions >= max(2, len(states) // 2):
        return "alternating_visible_subjects"
    return "fragmented_continuity"


def _density(frames):
    if len(frames) < 2:
        return {"classification": "insufficient_evidence", "average_elements": 0.0,
                "focal_stability": "unavailable"}
    geometric = any(
        frame.get("prominent_region_count") is not None for frame in frames
    )
    if geometric:
        counts = [
            int(_number(frame.get("prominent_region_count")))
            for frame in frames
        ]
        dominance = [
            _number(frame.get("focal_dominance_score"))
            for frame in frames
        ]
        competition = [
            _number(frame.get("focal_competition_score"))
            for frame in frames
        ]
        centroids = [
            frame.get("focal_centroid") for frame in frames
            if isinstance(frame.get("focal_centroid"), (list, tuple))
            and len(frame.get("focal_centroid")) == 2
        ]
        if centroids:
            center = (
                median([float(item[0]) for item in centroids]),
                median([float(item[1]) for item in centroids]),
            )
            drift = mean_distance = sum(
                math.dist((float(item[0]), float(item[1])), center)
                for item in centroids
            ) / len(centroids)
        else:
            drift = mean_distance = None
        average = sum(counts) / len(counts)
        average_dominance = sum(dominance) / len(dominance)
        average_competition = sum(competition) / len(competition)
        stable = (
            mean_distance is not None
            and mean_distance <= 0.08
            and average_dominance >= 0.52
            and average_competition < 0.52
        )
        if average >= 1.6 and average_competition >= 0.52:
            classification = "high_density_competing_focal_regions"
        elif stable and average >= 1.0:
            classification = "high_density_stable_focal_anchor"
        else:
            classification = "low_density"
        confidence_values = [
            str(frame.get("focal_structure_confidence") or "limited")
            for frame in frames
        ]
        confidence = (
            "high" if confidence_values.count("high") >= len(frames) * 0.6
            else "moderate" if any(value != "limited" for value in confidence_values)
            else "limited"
        )
        return {
            "classification": classification,
            "density_level": "high" if average >= 1.6 else "low",
            "average_elements": round(average, 3),
            "average_visible_elements": round(average, 3),
            "focal_stability": "stable" if stable else "variable",
            "focal_centroid_drift": round(drift, 3) if drift is not None else None,
            "focal_dominance_score": round(average_dominance, 3),
            "focal_competition_score": round(average_competition, 3),
            "element_counts": counts,
            "confidence": confidence,
            "provenance": "frame_observations.prominent_regions",
        }
    element_counts, focal = [], []
    for frame in frames:
        state = _state(frame)
        element_counts.append(
            state["subject_count"] + int(state["text"]) + state["graphic_regions"]
            + int(state["scene"] != "unavailable")
        )
        focal.append(state["focal_region"])
    average = sum(element_counts) / len(element_counts)
    known_focal = [value for value in focal if value != "unavailable"]
    focal_stable = bool(known_focal) and len(set(known_focal)) == 1
    if average < 2:
        classification = "low_density"
    elif focal_stable:
        classification = "high_density_stable_focal_anchor"
    else:
        classification = "high_density_competing_focal_regions"
    return {"classification": classification, "average_elements": round(average, 3),
            "average_visible_elements": round(average, 3),
            "focal_stability": "stable" if focal_stable else "variable",
            "element_counts": element_counts}


def _finding(identifier, kind, frames, measured, supporting, *, qualified=True,
             strength="moderate", limitations=None, conflicts=None):
    start = _number(frames[0].get("timestamp")) if frames else 0.0
    end = _number(frames[-1].get("timestamp")) if frames else 0.0
    conflicts = list(conflicts or [])
    if not frames:
        availability, result, strength = "unavailable", "not_qualified", "limited"
    elif conflicts:
        availability, result = "conflicting", "not_qualified"
    elif qualified:
        availability, result = "available_and_qualified", "qualified"
    else:
        availability, result = "available_but_weak", "not_qualified"
    return EvidenceFinding(
        identifier, kind, start, end, measured, evidence_strength=strength,
        supporting_observations=list(supporting), conflicting_observations=conflicts,
        availability_state=availability, qualification_result=result,
        limitations=list(limitations or []),
    )


def build_intelligence_v3(frame_observations, benchmark_context=None):
    """Build typed temporal findings without interpreting them as performance."""
    frames = [dict(item) for item in frame_observations or [] if isinstance(item, Mapping)]
    frames.sort(key=lambda item: _number(item.get("timestamp")))
    events = _events(frames)
    change_timestamps = sorted({event.timestamp for event in events})
    stable = _stable_intervals(frames, events)
    longest = max(stable, key=lambda item: item["duration"], default={
        "start_time": 0.0, "end_time": 0.0, "duration": 0.0,
    })
    intervals = [round(right - left, 3)
                 for left, right in zip(change_timestamps, change_timestamps[1:])]
    cadence = {
        "intervals": intervals,
        "median_interval": round(median(intervals), 3) if intervals else None,
        "shortest_interval": min(intervals) if intervals else None,
        "longest_interval": max(intervals) if intervals else None,
        "consistency": (
            "insufficient_evidence" if len(intervals) < 2 else
            "consistent" if max(intervals) - min(intervals) <= max(0.25, median(intervals) * 0.35)
            else "variable"
        ),
        "progression": _progression(intervals),
    }
    novelty_values = [
        round(_number(frame.get("perceptual_novelty_score")), 3)
        for frame in frames[1:]
        if frame.get("perceptual_novelty_score") is not None
    ]
    if not novelty_values:
        novelty_values = [event.novelty_score for event in events]
    novelty = {
        "scores": novelty_values,
        "average": round(sum(novelty_values) / len(novelty_values), 3)
        if novelty_values else None,
        "progression": _progression(novelty_values),
        "near_duplicate_transition_count": sum(value <= 0.2 for value in novelty_values),
    }
    introductions = [event for event in events if (
        event.event_type in {"scene_change", "composition_change", "dominant_subject_change"}
        or event.event_type == "text_overlay_change" and event.new_state is True
        or event.event_type == "subject_count_change" and event.new_state > event.previous_state
    )]
    first_time = _number(frames[0].get("timestamp")) if frames else 0.0
    end_time = _number(frames[-1].get("timestamp")) if frames else 0.0
    information = {
        "time_to_first_event": round(introductions[0].timestamp - first_time, 3)
        if introductions else None,
        "event_count": len(introductions),
        "timestamps": sorted({event.timestamp for event in introductions}),
        "rate_per_second": round(len(introductions) / max(end_time - first_time, 1.0), 3),
        "periods_without_new_information": stable,
    }
    density = _density(frames)
    scene_cut_timestamps = sorted({
        event.timestamp for event in events if event.event_type == "scene_change"
    })
    sample_span = max(end_time - first_time, 0.0)
    if sample_span > 0:
        cut_boundaries = [first_time, *scene_cut_timestamps, end_time]
        cut_intervals = [
            max(0.0, right - left)
            for left, right in zip(cut_boundaries, cut_boundaries[1:])
        ]
        longest_cut_free_ratio = max(cut_intervals, default=sample_span) / sample_span
        cut_ratio = min(
            1.0, len(scene_cut_timestamps) / max(len(frames) - 1, 1)
        )
        scene_continuity = round(
            0.55 * (1.0 - cut_ratio) + 0.45 * longest_cut_free_ratio, 3
        )
    else:
        scene_continuity = None
    coverage = len(frames)
    qualified = coverage >= 3
    observation_confidence = "high" if coverage >= 8 else "moderate" if qualified else "limited"
    interpretation_confidence = (
        "moderate" if qualified and events else "limited"
    )
    recommendation_confidence = (
        "moderate" if qualified and len(events) >= 1 else "limited"
    )
    event_dicts = [event.to_dict() for event in events]
    findings = [
        _finding("v3-change-timing", "meaningful_visual_change", frames, {
            "time_to_first_change": round(change_timestamps[0] - first_time, 3)
            if change_timestamps else None,
            "change_count": len(change_timestamps),
            "timestamps": change_timestamps,
            "longest_stable_interval": longest,
            "early_window_change_count": sum(timestamp <= first_time + 5 for timestamp in change_timestamps),
            "late_window_change_count": sum(timestamp > first_time + 5 for timestamp in change_timestamps),
            "scene_change_count": len(scene_cut_timestamps),
            "scene_continuity": scene_continuity,
            "scene_continuity_formula": (
                "0.55 * (1 - sampled_cut_ratio) + "
                "0.45 * longest_cut_free_interval_ratio"
            ),
        }, event_dicts, qualified=qualified, strength=observation_confidence,
                 limitations=["Sampled frames can miss changes between timestamps."]),
        _finding("v3-cadence", "visual_cadence", frames, cadence, event_dicts,
                 qualified=qualified and len(intervals) >= 2,
                 strength=interpretation_confidence,
                 limitations=["Cadence is unavailable until at least three meaningful changes exist."]),
        _finding("v3-novelty", "visual_novelty_progression", frames, novelty, event_dicts,
                 qualified=qualified and bool(events), strength=interpretation_confidence,
                 limitations=["Visual novelty is a measured difference, not a quality judgment."]),
        _finding("v3-information", "observable_information_introduction", frames, information,
                 [event.to_dict() for event in introductions], qualified=qualified,
                 strength=interpretation_confidence,
                 limitations=["Spoken information is excluded without qualified transcript evidence."]),
        _finding("v3-subject", "subject_continuity", frames, _subject_continuity(frames),
                 [{"sample": index, "subject_count": _state(frame)["subject_count"]}
                  for index, frame in enumerate(frames)], qualified=qualified,
                 strength=observation_confidence,
                 limitations=["Visible-subject continuity does not identify people."]),
        _finding("v3-density", "visual_density_and_focal_competition", frames, density,
                 [{"sample": index, "elements": value}
                  for index, value in enumerate(density.get("element_counts", []))],
                 qualified=qualified, strength=interpretation_confidence,
                 limitations=["Density describes simultaneous visible elements, not aesthetics."]),
    ]
    benchmark = dict(benchmark_context or {})
    benchmark_available = bool(
        (benchmark.get("benchmark_quality") or {}).get("eligible_for_directional_learning")
    )
    return {
        "version": "stratify-intelligence-v3",
        "sample_coverage": {
            "sample_count": coverage, "start_time": first_time, "end_time": end_time,
            "missing_windows": [],
        },
        "meaningful_change_events": event_dicts,
        "visual_change_timing": findings[0].measured_value,
        "visual_cadence": cadence,
        "visual_novelty": novelty,
        "information_introduction": information,
        "subject_continuity": findings[4].measured_value,
        "visual_density": density,
        "findings": [finding.to_dict() for finding in findings],
        "confidence": {
            "observation_confidence": observation_confidence,
            "interpretation_confidence": interpretation_confidence,
            "recommendation_confidence": recommendation_confidence,
            "reasons": [
                f"{coverage} sampled timestamp(s) were available.",
                "Recommendation confidence is calibrated separately from observation confidence.",
            ],
        },
        "benchmark_context": {
            "availability_state": (
                "available_and_qualified" if benchmark_available else "unavailable"
            ),
            "sample_size": len(benchmark.get("qualified") or
                               benchmark.get("qualified_benchmarks") or []),
            "limitations": [] if benchmark_available else [
                "No qualified benchmark context is available; findings use direct video evidence only."
            ],
        },
    }
