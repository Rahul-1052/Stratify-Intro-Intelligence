from typing import Any, Dict, List

from core.models.understanding_models import (
    TimestampedEvidence,
    TimelineSegment,
    ViewerContinuationSignal,
    VideoUnderstandingResult,
)


def understand_video_intro(
    video_id: str,
    frame_observations: List[Dict[str, Any]],
    intro_duration: float = 15.0,
    metadata: Dict[str, Any] | None = None,
) -> VideoUnderstandingResult:
    """
    Converts raw frame/OpenCV observations into structured intro understanding.

    This module does NOT recommend.
    This module does NOT compare benchmarks.
    This module only observes the first 15 seconds.
    """

    metadata = metadata or {}

    timeline = build_timeline(frame_observations)
    continuation_signals = extract_viewer_continuation_signals(timeline)

    summary = summarize_intro_observation(timeline, continuation_signals)
    confidence = estimate_confidence(frame_observations)

    return VideoUnderstandingResult(
        video_id=video_id,
        intro_duration=intro_duration,
        timeline=timeline,
        continuation_signals=continuation_signals,
        summary=summary,
        confidence=confidence,
        metadata=metadata,
    )


def build_timeline(frame_observations: List[Dict[str, Any]]) -> List[TimelineSegment]:
    segments: List[TimelineSegment] = []

    for obs in frame_observations:
        timestamp = float(obs.get("timestamp", 0.0))

        evidence = TimestampedEvidence(
            timestamp=timestamp,
            source="opencv_frame_analysis",
            observation=create_frame_observation_sentence(obs),
            raw_signals=obs,
        )

        segment = TimelineSegment(
            start_time=timestamp,
            end_time=timestamp + 1.0,
            observations=[evidence],
        )

        segments.append(segment)

    return segments


def create_frame_observation_sentence(obs: Dict[str, Any]) -> str:
    parts = []

    if obs.get("scene_type"):
        parts.append(f"scene appears to be {obs['scene_type']}")

    if obs.get("dominant_lighting"):
        parts.append(f"lighting is {obs['dominant_lighting']}")

    if obs.get("visual_energy"):
        parts.append(f"visual energy is {obs['visual_energy']}")

    if obs.get("human_presence") is not None:
        if obs.get("human_presence"):
            parts.append("human presence is detected")
        else:
            parts.append("no clear human presence is detected")

    if obs.get("text_overlay") is not None:
        if obs.get("text_overlay"):
            parts.append("text overlay is visible")
        else:
            parts.append("no text overlay is visible")

    if not parts:
        return "Frame contains limited detectable visual signals."

    return "Frame observation: " + ", ".join(parts) + "."


def extract_viewer_continuation_signals(
    timeline: List[TimelineSegment],
) -> List[ViewerContinuationSignal]:
    evidence = [
        item
        for segment in timeline
        for item in segment.observations
    ]

    return [
        ViewerContinuationSignal(
            signal_name="clarity",
            strength=estimate_clarity(evidence),
            reason="Clarity is estimated from visible subject presence, scene readability, and text/visual cues.",
            evidence=evidence,
        ),
        ViewerContinuationSignal(
            signal_name="momentum",
            strength=estimate_momentum(evidence),
            reason="Momentum is estimated from visual energy and changes across the intro timeline.",
            evidence=evidence,
        ),
        ViewerContinuationSignal(
            signal_name="curiosity",
            strength="unknown",
            reason="Curiosity requires deeper content/semantic understanding and should not be guessed from OpenCV alone.",
            evidence=evidence,
        ),
    ]


def estimate_clarity(evidence: List[TimestampedEvidence]) -> str:
    if not evidence:
        return "unknown"

    human_count = sum(
        1 for e in evidence
        if e.raw_signals.get("human_presence") is True
    )

    text_count = sum(
        1 for e in evidence
        if e.raw_signals.get("text_overlay") is True
    )

    if human_count >= 3 or text_count >= 3:
        return "high"

    if human_count >= 1 or text_count >= 1:
        return "moderate"

    return "low"


def estimate_momentum(evidence: List[TimestampedEvidence]) -> str:
    if not evidence:
        return "unknown"

    high_energy_count = sum(
        1 for e in evidence
        if str(e.raw_signals.get("visual_energy", "")).lower() == "high"
    )

    moderate_energy_count = sum(
        1 for e in evidence
        if str(e.raw_signals.get("visual_energy", "")).lower() == "moderate"
    )

    if high_energy_count >= 3:
        return "high"

    if high_energy_count >= 1 or moderate_energy_count >= 3:
        return "moderate"

    return "low"


def summarize_intro_observation(
    timeline: List[TimelineSegment],
    continuation_signals: List[ViewerContinuationSignal],
) -> str:
    if not timeline:
        return "No usable intro timeline was generated."

    signal_summary = ", ".join(
        f"{signal.signal_name}: {signal.strength}"
        for signal in continuation_signals
    )

    return (
        f"The first {timeline[-1].end_time:.0f} seconds were converted into "
        f"{len(timeline)} observed timeline segments. "
        f"Viewer continuation signals observed: {signal_summary}."
    )


def estimate_confidence(frame_observations: List[Dict[str, Any]]) -> str:
    count = len(frame_observations)

    if count >= 10:
        return "high"

    if count >= 5:
        return "moderate"

    if count >= 1:
        return "low"

    return "unknown"