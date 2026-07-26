"""Typed, JSON-safe product-validation contracts."""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ValidationDecision(str, Enum):
    USEFUL = "useful"
    PARTIALLY_USEFUL = "partially useful"
    NOT_USEFUL = "not useful"
    ABSTENTION_APPROPRIATE = "abstention appropriate"
    REQUIRES_HUMAN_REVIEW = "requires human review"


@dataclass
class ValidationScore:
    snapshot_accuracy: Optional[int] = None
    opportunity_specificity: Optional[int] = None
    experiment_actionability: Optional[int] = None
    confidence_believability: Optional[int] = None
    clarity: Optional[int] = None
    novelty: Optional[int] = None
    creator_usefulness: Optional[int] = None
    likelihood_of_acting: Optional[int] = None

    def validate(self):
        for name, value in asdict(self).items():
            if value is not None and (not isinstance(value, int) or not 1 <= value <= 5):
                raise ValueError(f"{name} must be an integer from 1 to 5 or null.")
        return self


@dataclass
class ValidationIssue:
    category: str
    severity: str
    section: str
    short_description: str
    supporting_evidence: str = ""
    expected_behavior: str = ""
    actual_behavior: str = ""
    reproducibility: str = "unknown"
    suggested_investigation: str = ""
    status: str = "requires human review"
    issue_id: str = ""
    case_id: str = ""


@dataclass
class ValidationCase:
    case_id: str
    source: str
    niche: str
    source_type: str
    normalized_video_id: str = ""
    creator_name: str = ""
    video_title: str = ""
    analysis_status: str = "pending"
    report_reference: str = ""
    reviewer_status: str = "awaiting human review"
    objective_warnings: List[Dict[str, Any]] = field(default_factory=list)
    score: ValidationScore = field(default_factory=ValidationScore)
    decision: ValidationDecision = ValidationDecision.REQUIRES_HUMAN_REVIEW
    reviewer_notes: str = ""
    one_change: str = ""
    issues: List[ValidationIssue] = field(default_factory=list)
    validation_kind: str = "real-video pipeline validation"

    def to_dict(self):
        value = asdict(self)
        value["decision"] = self.decision.value
        return value


@dataclass
class ValidationRun:
    run_id: str
    timestamp: str
    app_version: str
    git_commit: str
    validation_mode: str
    environment_notes: str = ""
    cases: List[ValidationCase] = field(default_factory=list)
    completed: bool = False

    def to_dict(self):
        return {**asdict(self), "cases": [case.to_dict() for case in self.cases]}
