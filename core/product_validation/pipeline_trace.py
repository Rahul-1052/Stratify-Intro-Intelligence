"""Typed, behavior-neutral pipeline tracing and stable failure classification."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List
import time

STAGES = ("acquisition", "clip preparation", "frame extraction", "temporal observation",
          "semantic observation", "benchmark discovery", "evidence qualification",
          "creative reasoning", "experiment generation", "report construction",
          "persistence", "reconstruction")
STATUSES = {"pending", "running", "completed", "completed_with_warnings",
            "skipped", "unavailable", "failed"}
TERMINAL = STATUSES - {"pending", "running"}

FAILURE_CATEGORIES = ("source unavailable", "network failure", "downloader failure",
    "unsupported media", "clip preparation failure", "frame extraction failure",
    "corrupt media", "observation failure", "benchmark failure",
    "evidence qualification failure", "reasoning failure",
    "report construction failure", "persistence failure", "reconstruction failure",
    "dependency failure", "environment failure", "unknown failure")


def now():
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PipelineStageTrace:
    stage_name: str
    stage_status: str = "pending"
    start_timestamp: str = ""
    end_timestamp: str = ""
    duration_seconds: float = 0.0
    warnings: List[str] = field(default_factory=list)
    error_type: str = ""
    error_message: str = ""
    evidence_counts: Dict[str, int] = field(default_factory=dict)
    output_references: List[str] = field(default_factory=list)
    retry_count: int = 0
    provenance: str = "direct trace"

    def transition(self, status, *, warnings=None, error=None, evidence_counts=None,
                   output_references=None, provenance=None):
        if status not in STATUSES:
            raise ValueError(f"Unsupported trace status: {status}")
        if self.stage_status in TERMINAL:
            raise ValueError(f"{self.stage_name} is already terminal.")
        if self.stage_status == "pending" and status not in {"running", "skipped", "unavailable", "failed"}:
            raise ValueError("A pending stage must start before completion.")
        if not self.start_timestamp:
            self.start_timestamp = now()
            self._started_clock = time.perf_counter()
        self.stage_status = status
        if warnings:
            self.warnings.extend(str(item) for item in warnings)
        if evidence_counts:
            self.evidence_counts.update({key: int(value or 0) for key, value in evidence_counts.items()})
        if output_references:
            self.output_references.extend(str(item) for item in output_references)
        if provenance:
            self.provenance = provenance
        if error:
            self.error_type = type(error).__name__
            self.error_message = str(error)
        if status in TERMINAL:
            self.end_timestamp = now()
            self.duration_seconds = round(max(time.perf_counter() - getattr(self, "_started_clock", time.perf_counter()), 0), 6)
        return self

    def to_dict(self):
        value = asdict(self)
        return value


@dataclass
class PipelineTrace:
    run_id: str
    case_id: str
    provenance: str
    stages: List[PipelineStageTrace] = field(default_factory=lambda: [PipelineStageTrace(name) for name in STAGES])
    failure_category: str = ""

    def stage(self, name):
        return next(item for item in self.stages if item.stage_name == name)

    @property
    def last_successful_stage(self):
        successful = []
        for item in self.stages:
            if item.stage_status == "failed":
                break
            if item.stage_status in {"completed", "completed_with_warnings"}:
                successful.append(item.stage_name)
        return successful[-1] if successful else ""

    @property
    def first_failed_stage(self):
        return next((item.stage_name for item in self.stages if item.stage_status == "failed"), "")

    def to_dict(self):
        return {"run_id": self.run_id, "case_id": self.case_id, "provenance": self.provenance,
                "failure_category": self.failure_category,
                "last_successful_stage": self.last_successful_stage,
                "first_failed_stage": self.first_failed_stage,
                "stages": [item.to_dict() for item in self.stages]}


def classify_failure(error=None, report=None, stage=""):
    text = " ".join((str(error or ""), str((report or {}).get("stage", "")),
                     " ".join(map(str, (report or {}).get("warnings", []) or [])))).lower()
    rules = (
        (("not found", "unavailable", "private video", "fetch video data"), "source unavailable"),
        (("network", "connection", "timeout", "dns"), "network failure"),
        (("yt-dlp", "downloader", "403", "forbidden"), "downloader failure"),
        (("unsupported", "codec", "format"), "unsupported media"),
        (("corrupt", "invalid data", "moov atom"), "corrupt media"),
        (("dependency", "module not found", "ffmpeg not"), "dependency failure"),
        (("environment", "permission", "access denied", "api_key", "api key"), "environment failure"),
    )
    for markers, category in rules:
        if any(marker in text for marker in markers):
            return category
    stage_categories = {"clip preparation": "clip preparation failure",
        "frame extraction": "frame extraction failure",
        "temporal observation": "observation failure", "semantic observation": "observation failure",
        "benchmark discovery": "benchmark failure", "evidence qualification": "evidence qualification failure",
        "creative reasoning": "reasoning failure", "experiment generation": "reasoning failure",
        "report construction": "report construction failure", "persistence": "persistence failure",
        "reconstruction": "reconstruction failure"}
    return stage_categories.get(stage, "unknown failure")


def evidence_counts(report):
    creator = report.get("creator_report") or {}
    observation = report.get("intro_observation") or report.get("observation") or {}
    temporal = report.get("temporal_evidence") or {}
    benchmarks = report.get("benchmark_intelligence") or report.get("benchmarks") or {}
    frames = report.get("frames") or report.get("frame_observations") or observation.get("frame_observations") or []
    windows = temporal.get("windows") or report.get("temporal_windows") or []
    candidates = benchmarks.get("candidates") or benchmarks.get("candidate_videos") or []
    qualified = benchmarks.get("qualified") or benchmarks.get("qualified_benchmarks") or []
    return {"sampled_frames": len(frames) if isinstance(frames, list) else int(frames.get("count", 0) or 0),
            "temporal_windows": len(windows) if isinstance(windows, list) else 0,
            "benchmark_candidates": len(candidates) if isinstance(candidates, list) else int(benchmarks.get("candidate_count", 0) or 0),
            "qualified_benchmarks": len(qualified) if isinstance(qualified, list) else int(benchmarks.get("qualified_count", 0) or 0),
            "supported_opportunities": int(bool((creator.get("biggest_opportunity") or {}).get("supported"))),
            "supported_experiments": len(creator.get("experiments") or [])}
