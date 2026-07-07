from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TimestampedEvidence:
    timestamp: float
    source: str
    observation: str
    raw_signals: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimelineSegment:
    start_time: float
    end_time: float
    observations: List[TimestampedEvidence] = field(default_factory=list)


@dataclass
class ViewerContinuationSignal:
    signal_name: str
    strength: str  # "low", "moderate", "high", "unknown"
    reason: str
    evidence: List[TimestampedEvidence] = field(default_factory=list)


@dataclass
class VideoUnderstandingResult:
    video_id: str
    intro_duration: float
    timeline: List[TimelineSegment]
    continuation_signals: List[ViewerContinuationSignal]
    summary: str
    confidence: str
    metadata: Dict[str, Any] = field(default_factory=dict)