from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Creator:
    id: str
    display_name: str
    created_at: str
    updated_at: str
    notes: str = ""
    primary_creator: bool = True


@dataclass(frozen=True)
class Channel:
    id: str
    creator_id: str
    platform: str
    channel_name: str
    created_at: str
    updated_at: str
    external_channel_id: Optional[str] = None
    channel_url: Optional[str] = None
    niche: Optional[str] = None
    notes: str = ""


@dataclass(frozen=True)
class VideoProject:
    id: str
    channel_id: str
    source_type: str
    analysis_status: str
    created_at: str
    analyzed_at: str
    external_video_id: Optional[str] = None
    source_url: Optional[str] = None
    title: Optional[str] = None
    published_at: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    source_fingerprint: Optional[str] = None


@dataclass(frozen=True)
class AnalysisRecord:
    id: str
    video_id: str
    analysis_version: str
    created_at: str
    snapshot: Dict[str, Any]
    creative_structure: Dict[str, Any]
    creative_understanding: Dict[str, Any]
    reasoning_summary: Dict[str, Any]
    opportunity: Dict[str, Any]
    experiments: List[Dict[str, Any]]
    confidence_summary: Dict[str, Any]
    evidence_limitations: List[str]
    analysis_completeness: str
    opening_strategy: Optional[str] = None
    primary_visual_focus: Optional[str] = None
    progression_style: Optional[str] = None
    subject_timing: Optional[str] = None
    subject_presence: Optional[str] = None
    multiple_subjects: Optional[bool] = None
    written_information_state: Optional[str] = None
    recommendation_state: Optional[str] = None
    recommendation_confidence: Optional[str] = None


@dataclass(frozen=True)
class Experiment:
    id: str
    analysis_id: str
    video_id: str
    dimension: str
    hypothesis: str
    change_description: str
    keep_constant: str
    version_a: str
    version_b: str
    confidence: str
    limitation: str
    status: str
    created_at: str
    updated_at: str
    result_summary: str = ""
    creator_notes: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass(frozen=True)
class MemorySnapshot:
    analyses_count: int = 0
    date_range: Optional[Dict[str, str]] = None
    patterns: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    strongest_stable_patterns: List[str] = field(default_factory=list)
    occasional_patterns: List[str] = field(default_factory=list)
    emerging_patterns: List[str] = field(default_factory=list)
    unexplored_experiment_dimensions: List[str] = field(default_factory=list)
    confidence: str = "insufficient_history"
    confidence_reasons: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)
