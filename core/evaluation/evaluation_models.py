"""Serializable contracts for evaluation datasets and runs."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvaluationVideo:
    video_id: str
    video_title: str
    source: str
    category: str
    url: str
    expected_manual_labels: Dict[str, Any] = field(default_factory=dict)
    notes: Optional[str] = None
    status: str = "unreviewed"
    evaluation_history: List[Dict[str, Any]] = field(default_factory=list)
    evaluation_id: str = ""
    reviewer_notes: Optional[str] = None
    _extra: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, value):
        allowed = cls.__dataclass_fields__
        known = {key: value[key] for key in allowed if key in value and key != "_extra"}
        if known.get("status") == "pending":
            known["status"] = "unreviewed"
        known["_extra"] = {key: item for key, item in value.items() if key not in allowed}
        return cls(**known)

    def to_dict(self):
        value = asdict(self)
        extra = value.pop("_extra", {})
        value.update(extra)
        return value


@dataclass
class FieldAgreement:
    field: str
    expected: Any
    predicted: Any
    result: str
    explanation: str

    def to_dict(self):
        return asdict(self)


@dataclass
class EvaluationResult:
    video_id: str
    video_title: str
    category: str
    status: str
    generation_seconds: float
    report: Dict[str, Any]
    agreements: List[FieldAgreement] = field(default_factory=list)
    cache_used: bool = False
    error: Optional[str] = None

    def to_dict(self):
        value = asdict(self)
        value["agreements"] = [item.to_dict() for item in self.agreements]
        return value


@dataclass
class EvaluationRun:
    run_id: str
    created_at: str
    dataset_name: str
    results: List[EvaluationResult]
    metrics: Dict[str, Any]
    failure_analysis: Dict[str, Any]

    def to_dict(self):
        return {
            "run_id": self.run_id, "created_at": self.created_at,
            "dataset_name": self.dataset_name,
            "results": [item.to_dict() for item in self.results],
            "metrics": self.metrics, "failure_analysis": self.failure_analysis,
        }
