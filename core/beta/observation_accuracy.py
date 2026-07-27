"""Observation Accuracy V1: transparent scoring over saved structured reports."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional


EVALUATION_VERSION = "observation-accuracy-v1"
ORDERED_VALUES = ("very_low", "low", "moderate", "high", "very_high")
STATUS_THRESHOLDS = (
    ("excellent", 0.90, 0.90),
    ("good", 0.75, 0.0),
    ("needs_review", 0.50, 0.0),
    ("poor", 0.0, 0.0),
)
COMPARISON_MODES = {
    "exact", "ordered", "numeric_min", "numeric_max", "numeric_range",
    "boolean", "temporal_before", "temporal_after", "relative", "presence",
}
CONFIDENCE_VALUES = {"high": 1.0, "moderate": 0.67, "limited": 0.33}


@dataclass(frozen=True)
class ExpectedObservation:
    metric: str
    expected_value: Any
    comparison: str
    tolerance: float = 0.0
    weight: float = 1.0
    required: bool = False
    description: str = ""

    @classmethod
    def from_dict(cls, value):
        return cls(**{key: value[key] for key in (
            "metric", "expected_value", "comparison", "tolerance", "weight",
            "required", "description",
        ) if key in value})


@dataclass(frozen=True)
class ObservedObservation:
    metric: str
    observed_value: Any
    confidence: float
    source: str
    timestamp: Optional[float] = None
    evidence: Any = None

    def to_dict(self):
        return asdict(self)


@dataclass
class MetricEvaluation:
    metric: str
    expected: Any
    observed: Any
    matched: bool
    score: Optional[float]
    confidence: Optional[float]
    comparison_method: str
    explanation: str
    evidence: Any = None
    mismatch_reason: str = ""
    required: bool = False
    weight: float = 1.0
    source: str = ""
    status: str = "evaluated"

    def to_dict(self):
        return asdict(self)


@dataclass
class CaseAccuracyResult:
    case_id: str
    case_title: str
    evaluated_metrics: List[MetricEvaluation] = field(default_factory=list)
    matched_metrics: int = 0
    partial_metrics: int = 0
    mismatched_metrics: int = 0
    unavailable_metrics: int = 0
    weighted_score: Optional[float] = None
    unweighted_score: Optional[float] = None
    evaluability_coverage: float = 0.0
    required_metric_coverage: float = 0.0
    status: str = "unevaluable"
    warnings: List[str] = field(default_factory=list)

    def to_dict(self):
        value = asdict(self)
        value["evaluated_metrics"] = [
            metric.to_dict() for metric in self.evaluated_metrics
        ]
        return value


@dataclass
class AccuracyRunSummary:
    run_id: str
    cases_evaluated: int
    completed_cases: int
    unevaluable_cases: int
    aggregate_weighted_accuracy: Optional[float]
    aggregate_unweighted_accuracy: Optional[float]
    evaluability_coverage: float
    required_metric_coverage: float
    accuracy_by_metric: Dict[str, Dict[str, Any]]
    average_confidence: Optional[float]
    mismatch_count: int
    unavailable_count: int
    weakest_metrics: List[Dict[str, Any]]
    strongest_metrics: List[Dict[str, Any]]
    timestamp: str
    evaluation_version: str = EVALUATION_VERSION
    case_results: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def _confidence(report, kind="observation_confidence"):
    value = str(
        ((report.get("intelligence_v3") or {}).get("confidence") or {}).get(
            kind, "limited"
        )
    ).lower()
    return CONFIDENCE_VALUES.get(value, 0.33)


def normalize_observations(report):
    """Adapt only structured observation fields; never inspect report prose."""
    vision = report.get("vision") or {}
    frames = [
        item for item in vision.get("frame_observations") or []
        if isinstance(item, dict)
    ]
    intelligence = report.get("intelligence_v3") or {}
    changes = intelligence.get("visual_change_timing") or {}
    cadence = intelligence.get("visual_cadence") or {}
    novelty = intelligence.get("visual_novelty") or {}
    density = intelligence.get("visual_density") or {}
    information = intelligence.get("information_introduction") or {}
    events = intelligence.get("meaningful_change_events") or []
    observation_confidence = _confidence(report)
    interpretation_confidence = _confidence(report, "interpretation_confidence")
    normalized = {}

    def add(metric, value, source, confidence=observation_confidence,
            timestamp=None, evidence=None, allow_none=False):
        if value is not None or allow_none:
            normalized[metric] = ObservedObservation(
                metric, value, confidence, source, timestamp, evidence,
            )

    add("visual_energy", vision.get("visual_energy") or vision.get("energy"),
        "vision.visual_energy", evidence={
            "sample_values": [item.get("visual_energy") for item in frames]
        })
    motion = [float(item["motion_score"]) for item in frames
              if item.get("motion_score") is not None]
    add("motion_score_mean", round(mean(motion), 3) if motion else None,
        "vision.frame_observations.motion_score", evidence={"samples": len(motion)})
    add("motion_score_max", round(max(motion), 3) if motion else None,
        "vision.frame_observations.motion_score", evidence={"samples": len(motion)})
    add("change_count", changes.get("change_count"),
        "intelligence_v3.visual_change_timing.change_count",
        evidence={"timestamps": changes.get("timestamps") or []})
    add("scene_change_count", sum(
        item.get("event_type") == "scene_change" for item in events
    ), "intelligence_v3.meaningful_change_events", evidence={
        "scene_change_timestamps": [
            item.get("timestamp") for item in events
            if item.get("event_type") == "scene_change"
        ]
    })
    span = (
        (intelligence.get("sample_coverage") or {}).get("end_time", 0)
        - (intelligence.get("sample_coverage") or {}).get("start_time", 0)
    )
    stable_duration = (changes.get("longest_stable_interval") or {}).get("duration")
    calibrated_continuity = changes.get("scene_continuity")
    add("scene_continuity", calibrated_continuity if calibrated_continuity is not None
        else round(float(stable_duration) / span, 3)
        if stable_duration is not None and span > 0 else None,
        (
            "intelligence_v3.visual_change_timing.scene_continuity"
            if calibrated_continuity is not None
            else "intelligence_v3.visual_change_timing.longest_stable_interval"
        ),
        interpretation_confidence, evidence={
            "sample_span": span,
            "scene_change_count": changes.get("scene_change_count"),
            "formula": changes.get("scene_continuity_formula"),
        })
    add("cadence_progression", cadence.get("progression"),
        "intelligence_v3.visual_cadence.progression", interpretation_confidence)
    add("cadence_interval_median", cadence.get("median_interval"),
        "intelligence_v3.visual_cadence.median_interval", interpretation_confidence)
    add("novelty_mean", novelty.get("average"),
        "intelligence_v3.visual_novelty.average", interpretation_confidence,
        evidence={"scores": novelty.get("scores") or []})
    subject_frames = [item for item in frames if (
        item.get("human_presence") or int(item.get("subject_count") or 0) > 0
    )]
    subject_intro = (
        min(float(item.get("timestamp") or 0) for item in subject_frames)
        if subject_frames else None
    )
    add("subject_intro_seconds", subject_intro,
        "vision.frame_observations.human_presence",
        timestamp=subject_intro, evidence={"present_samples": len(subject_frames)},
        allow_none=True)
    add("subject_initially_present", bool(subject_frames and subject_intro == 0),
        "vision.frame_observations.human_presence",
        evidence={"first_sample_timestamp": frames[0].get("timestamp") if frames else None})
    add("subject_presence_ratio",
        round(len(subject_frames) / len(frames), 3) if frames else None,
        "vision.frame_observations.human_presence")
    add("subject_continuity", intelligence.get("subject_continuity"),
        "intelligence_v3.subject_continuity", interpretation_confidence)
    text_frames = [item for item in frames if item.get("text_overlay") is True]
    text_intro = (
        min(float(item.get("timestamp") or 0) for item in text_frames)
        if text_frames else None
    )
    text_confidence = min(
        (CONFIDENCE_VALUES.get(str(item.get("text_overlay_confidence")).lower(), 0.33)
         for item in text_frames), default=0.33,
    )
    add("text_intro_seconds", text_intro,
        "vision.frame_observations.text_overlay", text_confidence,
        timestamp=text_intro, evidence={"present_samples": len(text_frames)},
        allow_none=True)
    add("text_initially_present", bool(text_frames and text_intro == 0),
        "vision.frame_observations.text_overlay", text_confidence)
    add("text_presence_ratio",
        round(len(text_frames) / len(frames), 3) if frames else None,
        "vision.frame_observations.text_overlay", text_confidence,
        evidence={"timestamps": [item.get("timestamp") for item in text_frames]})
    add("text_present", bool(text_frames),
        "vision.frame_observations.text_overlay", text_confidence,
        evidence={"timestamps": [item.get("timestamp") for item in text_frames]})
    add("information_intro_seconds", information.get("time_to_first_event"),
        "intelligence_v3.information_introduction.time_to_first_event",
        interpretation_confidence)
    add("information_event_count", information.get("event_count"),
        "intelligence_v3.information_introduction.event_count",
        interpretation_confidence)
    density_confidence = CONFIDENCE_VALUES.get(
        str(density.get("confidence") or "limited").lower(),
        interpretation_confidence,
    )
    add("density_classification", density.get("classification"),
        "intelligence_v3.visual_density.classification",
        density_confidence, evidence={
            "dominance": density.get("focal_dominance_score"),
            "competition": density.get("focal_competition_score"),
            "centroid_drift": density.get("focal_centroid_drift"),
        })
    visible_elements = density.get(
        "average_visible_elements", density.get("average_elements")
    )
    add("average_visible_elements", visible_elements,
        "intelligence_v3.visual_density.average_visible_elements"
        if density.get("average_visible_elements") is not None
        else "intelligence_v3.visual_density.average_elements",
        density_confidence)
    add("focal_stability", density.get("focal_stability"),
        "intelligence_v3.visual_density.focal_stability",
        density_confidence, evidence={
            "centroid_drift": density.get("focal_centroid_drift"),
            "dominance": density.get("focal_dominance_score"),
            "competition": density.get("focal_competition_score"),
        })
    return normalized


def evaluate_metric(expected, observed):
    if expected.comparison not in COMPARISON_MODES:
        raise ValueError(f"Unsupported comparison mode: {expected.comparison}")
    if observed is None:
        return MetricEvaluation(
            expected.metric, expected.expected_value, None, False, None, None,
            expected.comparison, "The structured report did not expose this metric.",
            mismatch_reason="Observation unavailable.", required=expected.required,
            weight=expected.weight, status="unavailable",
        )
    actual, target, mode = observed.observed_value, expected.expected_value, expected.comparison
    score = 0.0
    explanation = ""
    try:
        if mode == "exact":
            score = float(actual == target)
        elif mode == "ordered":
            expected_index = ORDERED_VALUES.index(str(target))
            actual_index = ORDERED_VALUES.index(str(actual))
            distance = abs(expected_index - actual_index)
            score = 1.0 if distance == 0 else 0.5 if distance <= expected.tolerance else 0.0
        elif mode in {"numeric_min", "temporal_after"}:
            if actual is None:
                return _unavailable_metric(expected, observed)
            score = float(float(actual) >= float(target))
        elif mode in {"numeric_max", "temporal_before"}:
            if actual is None:
                return _unavailable_metric(expected, observed)
            score = float(float(actual) <= float(target))
        elif mode == "numeric_range":
            score = float(float(target[0]) <= float(actual) <= float(target[1]))
        elif mode == "boolean":
            score = float(bool(actual) is bool(target))
        elif mode == "relative":
            operator, value = target["operator"], float(target["value"])
            score = float({
                "gt": float(actual) > value, "gte": float(actual) >= value,
                "lt": float(actual) < value, "lte": float(actual) <= value,
            }[operator])
        elif mode == "presence":
            present = actual is not None
            score = float(present if target == "present" else not present)
        explanation = (
            f"Observed {actual!r}; expected {target!r} using {mode}."
            + (" Within the accepted ordered tolerance." if score == 0.5 else "")
        )
    except (TypeError, ValueError, KeyError, IndexError) as exc:
        raise ValueError(
            f"Invalid {mode} comparison for metric {expected.metric}: {exc}"
        ) from exc
    matched = score == 1.0
    return MetricEvaluation(
        expected.metric, target, actual, matched, score, observed.confidence,
        mode, explanation, observed.evidence,
        "" if score > 0 else f"Observed value {actual!r} did not satisfy {mode} expectation {target!r}.",
        expected.required, expected.weight, observed.source,
        "matched" if matched else "partial" if score > 0 else "mismatched",
    )


def _unavailable_metric(expected, observed):
    return MetricEvaluation(
        expected.metric, expected.expected_value, None, False, None,
        observed.confidence, expected.comparison,
        "The metric exists structurally but no observation was available.",
        observed.evidence, "Observation unavailable.", expected.required,
        expected.weight, observed.source, "unavailable",
    )


def console_summary(summary, accuracy_path):
    lines = [
        "Observation Accuracy V1",
        f"Cases evaluated: {summary.cases_evaluated}",
        f"Metrics evaluated: {sum(value['evaluated'] for value in summary.accuracy_by_metric.values())}",
        f"Weighted accuracy: {_percent(summary.aggregate_weighted_accuracy)}",
        f"Evaluability coverage: {_percent(summary.evaluability_coverage)}",
        f"Required metric coverage: {_percent(summary.required_metric_coverage)}",
        f"Unavailable metrics: {summary.unavailable_count}",
        "", "Weakest metrics:",
    ]
    lines.extend(
        f"{index}. {item['metric']} — {_percent(item['accuracy'])}"
        for index, item in enumerate(summary.weakest_metrics[:3], 1)
    )
    lines.extend(["", "Saved:", str(accuracy_path)])
    return "\n".join(lines)


def _status(accuracy, coverage):
    if accuracy is None:
        return "unevaluable"
    for name, minimum_accuracy, minimum_coverage in STATUS_THRESHOLDS:
        if accuracy >= minimum_accuracy and coverage >= minimum_coverage:
            return name
    return "poor"


def evaluate_case(case, report):
    expectations = [
        ExpectedObservation.from_dict(item)
        for item in case.get("expected_observations") or []
    ]
    if not expectations:
        return CaseAccuracyResult(
            case.get("case_id", ""), case.get("case_title") or case.get("case_id", ""),
            warnings=["No machine-readable expected observations are defined."],
        )
    observed = normalize_observations(report)
    metrics = [evaluate_metric(item, observed.get(item.metric)) for item in expectations]
    evaluated = [item for item in metrics if item.score is not None]
    required = [item for item in metrics if item.required]
    required_evaluated = [item for item in required if item.score is not None]
    weight_total = sum(item.weight for item in evaluated)
    weighted = (
        sum(item.score * item.weight for item in evaluated) / weight_total
        if weight_total else None
    )
    unweighted = mean(item.score for item in evaluated) if evaluated else None
    coverage = len(evaluated) / len(metrics) if metrics else 0.0
    required_coverage = (
        len(required_evaluated) / len(required) if required else 1.0
    )
    warnings = [
        f"Required metric unavailable: {item.metric}"
        for item in required if item.score is None
    ]
    return CaseAccuracyResult(
        case.get("case_id", ""), case.get("case_title") or case.get("case_id", ""),
        metrics, sum(item.score == 1 for item in evaluated),
        sum(0 < item.score < 1 for item in evaluated),
        sum(item.score == 0 for item in evaluated),
        sum(item.score is None for item in metrics),
        round(weighted, 4) if weighted is not None else None,
        round(unweighted, 4) if unweighted is not None else None,
        round(coverage, 4), round(required_coverage, 4),
        _status(weighted, coverage), warnings,
    )


def aggregate_results(run_id, results, timestamp=""):
    metrics = {}
    all_evaluations = []
    for case in results:
        for item in case.evaluated_metrics:
            entry = metrics.setdefault(item.metric, {
                "evaluated": 0, "correct": 0, "partial": 0,
                "incorrect": 0, "unavailable": 0, "scores": [], "confidences": [],
            })
            if item.score is None:
                entry["unavailable"] += 1
            else:
                entry["evaluated"] += 1
                entry["scores"].append(item.score)
                entry["confidences"].append(item.confidence)
                entry["correct" if item.score == 1 else "partial" if item.score > 0 else "incorrect"] += 1
                all_evaluations.append(item)
    metric_summary = {}
    for metric, entry in sorted(metrics.items()):
        scores, confidences = entry.pop("scores"), entry.pop("confidences")
        metric_summary[metric] = {
            **entry,
            "accuracy": round(mean(scores), 4) if scores else None,
            "average_confidence": round(mean(confidences), 4) if confidences else None,
        }
    ranked = [
        {"metric": metric, **value} for metric, value in metric_summary.items()
        if value["accuracy"] is not None
    ]
    ranked.sort(key=lambda item: (item["accuracy"], item["metric"]))
    total_expected = sum(len(item.evaluated_metrics) for item in results)
    total_evaluated = len(all_evaluations)
    required_total = sum(
        metric.required for item in results for metric in item.evaluated_metrics
    )
    required_evaluated = sum(
        metric.required and metric.score is not None
        for item in results for metric in item.evaluated_metrics
    )
    weights = sum(item.weight for item in all_evaluations)
    return AccuracyRunSummary(
        run_id, len(results), sum(item.status != "unevaluable" for item in results),
        sum(item.status == "unevaluable" for item in results),
        round(sum(item.score * item.weight for item in all_evaluations) / weights, 4)
        if weights else None,
        round(mean(item.score for item in all_evaluations), 4)
        if all_evaluations else None,
        round(total_evaluated / total_expected, 4) if total_expected else 0.0,
        round(required_evaluated / required_total, 4) if required_total else 1.0,
        metric_summary,
        round(mean(item.confidence for item in all_evaluations), 4)
        if all_evaluations else None,
        sum(item.score == 0 for item in all_evaluations),
        sum(item.score is None for case in results for item in case.evaluated_metrics),
        ranked[:5], list(reversed(ranked[-5:])), timestamp,
        case_results=[item.to_dict() for item in results],
    )


def evaluate_saved_run(run_dir, manifest_path):
    run_dir, manifest_path = Path(run_dir), Path(manifest_path)
    run = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = {item["case_id"]: item for item in manifest.get("cases") or []}
    results, warnings = [], []
    for run_case in run.get("cases") or []:
        case_id = run_case.get("case_id")
        if run_case.get("status") != "completed":
            warnings.append(f"{case_id}: run case is not completed.")
            continue
        case = cases.get(case_id)
        report_path = run_dir / str(run_case.get("report_path") or "")
        if not case or not report_path.is_file():
            warnings.append(f"{case_id}: expectation or saved report is unavailable.")
            continue
        report = json.loads(report_path.read_text(encoding="utf-8"))
        results.append(evaluate_case(case, report))
    summary = aggregate_results(
        run.get("run_id", run_dir.name), results, run.get("timestamp", "")
    )
    summary.warnings.extend(warnings)
    accuracy = run_dir / "accuracy"
    cases_dir = accuracy / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    for result in results:
        _write_json(cases_dir / f"{result.case_id}.json", result.to_dict())
    _write_json(accuracy / "summary.json", summary.to_dict())
    (accuracy / "summary.md").write_text(
        accuracy_markdown(summary), encoding="utf-8", newline="\n"
    )
    return summary, accuracy


def latest_completed_run(runs_dir):
    candidates = []
    for path in Path(runs_dir).iterdir() if Path(runs_dir).is_dir() else []:
        summary = path / "summary.json"
        if summary.is_file():
            try:
                payload = json.loads(summary.read_text(encoding="utf-8"))
                if any(item.get("status") == "completed" for item in payload.get("cases") or []):
                    candidates.append(path)
            except (OSError, json.JSONDecodeError):
                continue
    return sorted(candidates, key=lambda item: item.name)[-1] if candidates else None


def _write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )


def _percent(value):
    return "Unavailable" if value is None else f"{value * 100:.1f}%"


def accuracy_markdown(summary):
    lines = [
        "# Observation Accuracy V1", "", "## Overall", "",
        f"- Cases evaluated: {summary.cases_evaluated}",
        f"- Metrics evaluated: {sum(v['evaluated'] for v in summary.accuracy_by_metric.values())}",
        f"- Weighted accuracy: {_percent(summary.aggregate_weighted_accuracy)}",
        f"- Unweighted accuracy: {_percent(summary.aggregate_unweighted_accuracy)}",
        f"- Evaluability coverage: {_percent(summary.evaluability_coverage)}",
        f"- Required metric coverage: {_percent(summary.required_metric_coverage)}",
        f"- Unavailable metrics: {summary.unavailable_count}",
        f"- Average confidence: {_percent(summary.average_confidence)}",
        "", "## Accuracy by metric", "",
        "| Metric | Evaluated | Correct | Partial | Incorrect | Unavailable | Accuracy | Average confidence |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for metric, value in summary.accuracy_by_metric.items():
        lines.append(
            f"| {metric} | {value['evaluated']} | {value['correct']} | "
            f"{value['partial']} | {value['incorrect']} | {value['unavailable']} | "
            f"{_percent(value['accuracy'])} | {_percent(value['average_confidence'])} |"
        )
    lines.extend(["", "## Case results", "",
                  "| Case | Score | Matched | Mismatched | Unavailable | Status |",
                  "|---|---:|---:|---:|---:|---|"])
    for case in summary.case_results:
        lines.append(
            f"| {case['case_id']} | {_percent(case['weighted_score'])} | "
            f"{case['matched_metrics']} | {case['mismatched_metrics']} | "
            f"{case['unavailable_metrics']} | {case['status']} |"
        )
    for heading, items in (
        ("Weakest observations", summary.weakest_metrics),
        ("Strongest observations", summary.strongest_metrics),
    ):
        lines.extend(["", f"## {heading}", ""])
        lines.extend(
            f"{index}. {item['metric']} — {_percent(item['accuracy'])}"
            for index, item in enumerate(items, 1)
        )
    lines.extend(["", "## Detailed mismatches", ""])
    mismatches = [
        (case, metric) for case in summary.case_results
        for metric in case["evaluated_metrics"] if metric["score"] == 0
    ]
    if not mismatches:
        lines.append("No evaluated mismatches.")
    for case, metric in mismatches:
        lines.extend([
            f"### {case['case_id']} · {metric['metric']}", "",
            f"- Expected: `{metric['expected']}`",
            f"- Observed: `{metric['observed']}`",
            f"- Comparison: `{metric['comparison_method']}`",
            f"- Confidence: {_percent(metric['confidence'])}",
            f"- Explanation: {metric['mismatch_reason']}",
            f"- Source: `{metric['source']}`",
            f"- Evidence: `{json.dumps(metric['evidence'], sort_keys=True)}`", "",
        ])
    return "\n".join(lines) + "\n"
