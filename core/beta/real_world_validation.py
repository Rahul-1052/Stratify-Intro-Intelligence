"""Blind, offline-first validation for manually supplied real-world clips."""

import hashlib
import json
import re
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from core.beta.observation_accuracy import (
    COMPARISON_MODES,
    ExpectedObservation,
    accuracy_markdown,
    aggregate_results,
    evaluate_case,
    normalize_observations,
)


SCHEMA_VERSION = 1
VALIDATION_VERSION = "real-world-validation-v1"
REQUIRED_CASE_FIELDS = {
    "case_id", "title", "category", "clip_path", "source_type",
    "duration_seconds", "enabled", "notes", "expectations",
    "annotation_status", "annotator", "created_at",
    "expectations_created_at", "analysis_started_at", "expectations_hash",
}
ANNOTATION_METRICS = (
    "scene_change_count", "scene_continuity", "novelty_mean",
    "motion_score_mean", "visual_energy", "text_initially_present",
    "text_intro_seconds", "text_presence_ratio", "subject_initially_present",
    "subject_intro_seconds", "subject_presence_ratio", "focal_stability",
    "density_classification", "average_visible_elements",
)
CASE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def expectation_hash(expectations):
    canonical = json.dumps(
        expectations or [], ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_expectations(expectations, case_id):
    if not isinstance(expectations, list):
        raise ValueError(f"{case_id}: expectations must be a list.")
    seen = set()
    for index, raw in enumerate(expectations):
        if not isinstance(raw, dict):
            raise ValueError(f"{case_id}: expectation {index + 1} must be an object.")
        try:
            parsed = ExpectedObservation.from_dict(raw)
        except (KeyError, TypeError) as exc:
            raise ValueError(
                f"{case_id}: expectation {index + 1} is incomplete."
            ) from exc
        if not parsed.metric:
            raise ValueError(f"{case_id}: expectation {index + 1} has no metric.")
        if parsed.metric in seen:
            raise ValueError(f"{case_id}: duplicate expectation for {parsed.metric}.")
        if parsed.comparison not in COMPARISON_MODES:
            raise ValueError(
                f"{case_id}: unsupported comparison {parsed.comparison!r}."
            )
        seen.add(parsed.metric)


def load_manifest(path):
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise ValueError("Real-world manifest cases must be a list.")
    seen = set()
    cases = []
    for index, raw in enumerate(payload["cases"]):
        if not isinstance(raw, dict):
            raise ValueError(f"Case {index + 1} must be an object.")
        missing = REQUIRED_CASE_FIELDS.difference(raw)
        if missing:
            raise ValueError(
                f"Case {index + 1} is missing: {', '.join(sorted(missing))}"
            )
        case_id = str(raw["case_id"]).strip()
        if not CASE_ID_PATTERN.fullmatch(case_id) or case_id in seen:
            raise ValueError(f"Duplicate or invalid case ID: {case_id!r}")
        if not isinstance(raw["enabled"], bool):
            raise ValueError(f"{case_id}: enabled must be boolean.")
        _validate_expectations(raw["expectations"], case_id)
        seen.add(case_id)
        cases.append({**raw, "case_id": case_id, "_manifest_dir": str(source.parent)})
    return {
        "schema_version": payload.get("schema_version", SCHEMA_VERSION),
        "validation_version": payload.get("validation_version", VALIDATION_VERSION),
        "cases": cases,
    }


def save_manifest(path, payload):
    clean = {
        "schema_version": payload.get("schema_version", SCHEMA_VERSION),
        "validation_version": payload.get("validation_version", VALIDATION_VERSION),
        "cases": [
            {key: value for key, value in case.items() if not key.startswith("_")}
            for case in payload.get("cases", [])
        ],
    }
    _write_json(Path(path), clean)


def validate_clip(path):
    import cv2

    source = Path(path)
    if not source.is_file():
        return {"valid": False, "reason": "Clip file does not exist."}
    capture = cv2.VideoCapture(str(source))
    try:
        if not capture.isOpened():
            return {"valid": False, "reason": "Clip could not be opened."}
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        duration = frame_count / fps if frame_count > 0 and fps > 0 else 0.0
        valid = frame_count > 0 and fps > 0
        return {
            "valid": valid,
            "reason": "" if valid else "Clip has no readable video frames.",
            "frame_count": frame_count,
            "fps": round(fps, 3),
            "duration_seconds": round(duration, 3),
            "size_bytes": source.stat().st_size,
        }
    finally:
        capture.release()


def create_case(manifest_path, case_id, title, category, clip_path,
                copy_clip=True, source_type="local_file", notes="", now=None):
    manifest_path, source = Path(manifest_path), Path(clip_path).resolve()
    if not CASE_ID_PATTERN.fullmatch(case_id):
        raise ValueError("case_id may contain letters, numbers, dots, dashes, and underscores.")
    validation = validate_clip(source)
    if not validation["valid"]:
        raise ValueError(f"Invalid clip: {validation['reason']}")
    manifest = load_manifest(manifest_path)
    if any(item["case_id"] == case_id for item in manifest["cases"]):
        raise ValueError(f"Case already exists: {case_id}")
    if copy_clip:
        destination = manifest_path.parent / "clips" / (
            f"{case_id}{source.suffix.lower()}"
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise ValueError(f"Destination clip already exists: {destination}")
        shutil.copy2(source, destination)
        stored_path = destination.relative_to(manifest_path.parent).as_posix()
    else:
        stored_path = str(source)
    timestamp = now or utc_now()
    case = {
        "case_id": case_id,
        "title": title,
        "category": category,
        "clip_path": stored_path,
        "source_type": source_type,
        "duration_seconds": validation["duration_seconds"],
        "enabled": True,
        "notes": notes,
        "expectations": [],
        "annotation_status": "not_started",
        "annotator": "",
        "created_at": timestamp,
        "expectations_created_at": "",
        "analysis_started_at": "",
        "expectations_hash": "",
    }
    manifest["cases"].append(case)
    save_manifest(manifest_path, manifest)
    return case


def lock_expectations(manifest_path, case_id, annotator="", now=None):
    manifest = load_manifest(manifest_path)
    case = _find_case(manifest, case_id)
    if case["analysis_started_at"]:
        raise ValueError("Expectations cannot be locked after analysis has begun.")
    case["expectations_hash"] = expectation_hash(case["expectations"])
    case["expectations_created_at"] = now or utc_now()
    case["annotation_status"] = "locked"
    case["annotator"] = annotator or case.get("annotator", "")
    save_manifest(manifest_path, manifest)
    return {key: value for key, value in case.items() if not key.startswith("_")}


def verify_expectations_lock(case):
    if case.get("annotation_status") != "locked":
        raise ValueError(f"{case['case_id']}: expectations are not locked.")
    expected_hash = case.get("expectations_hash", "")
    if not expected_hash:
        raise ValueError(f"{case['case_id']}: expectations hash is missing.")
    actual_hash = expectation_hash(case.get("expectations"))
    if actual_hash != expected_hash:
        raise ValueError(
            f"{case['case_id']}: expectations changed after they were locked."
        )
    if not case.get("expectations_created_at"):
        raise ValueError(f"{case['case_id']}: expectation timestamp is missing.")
    return True


def mark_analysis_started(manifest_path, case_ids, now=None):
    manifest = load_manifest(manifest_path)
    selected = [_find_case(manifest, case_id) for case_id in case_ids]
    for case in selected:
        verify_expectations_lock(case)
    timestamp = now or utc_now()
    for case in selected:
        if not case["analysis_started_at"]:
            case["analysis_started_at"] = timestamp
    save_manifest(manifest_path, manifest)
    return load_manifest(manifest_path)


def resolve_clip(case):
    path = Path(case["clip_path"])
    if not path.is_absolute():
        path = Path(case["_manifest_dir"]) / path
    return path.resolve()


class RealWorldValidationRunner:
    def __init__(self, analyzer=None):
        self.analyzer = analyzer or self._default_analyzer

    @staticmethod
    def _default_analyzer(clip_path, no_network=True):
        from stratify_platform.module_registry import run_module

        return run_module(
            "intro_intelligence", url="",
            intro_seconds=15, frame_fps=1,
            uploaded_video_path=str(clip_path),
            local_source_type="uploaded_file",
            no_network=no_network,
        )

    def run(self, manifest_path, case_ids=None, limit=None, output_dir=None,
            allow_network=False, run_id=None):
        manifest_path = Path(manifest_path)
        manifest = load_manifest(manifest_path)
        selected = [
            item for item in manifest["cases"]
            if item["enabled"] and (not case_ids or item["case_id"] in case_ids)
        ]
        if limit is not None:
            selected = selected[:max(limit, 0)]
        if not selected:
            raise ValueError("No enabled real-world cases were selected.")
        missing = sorted(set(case_ids or []).difference(
            item["case_id"] for item in selected
        ))
        if missing:
            raise ValueError(f"Unknown or disabled cases: {', '.join(missing)}")
        validations = {}
        for case in selected:
            check = validate_clip(resolve_clip(case))
            if not check["valid"]:
                raise ValueError(f"{case['case_id']}: {check['reason']}")
            validations[case["case_id"]] = check
            verify_expectations_lock(case)
        manifest = mark_analysis_started(
            manifest_path, [item["case_id"] for item in selected]
        )
        selected_by_id = {item["case_id"]: item for item in manifest["cases"]}
        selected = [selected_by_id[item["case_id"]] for item in selected]

        run_id = run_id or (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "-" + uuid.uuid4().hex[:8]
        )
        root = Path(output_dir or manifest_path.parent / "runs") / run_id
        raw_dir, accuracy_cases = root / "cases", root / "accuracy" / "cases"
        raw_dir.mkdir(parents=True, exist_ok=False)
        accuracy_cases.mkdir(parents=True, exist_ok=True)
        started_at = utc_now()
        run_cases, accuracy_results = [], []
        for case in selected:
            clip = resolve_clip(case)
            case_started = utc_now()
            clock = time.perf_counter()
            try:
                # Deliberately pass only the clip and network policy. Expectations
                # never enter the observation pipeline.
                report = self.analyzer(clip, no_network=not allow_network)
                runtime = round(time.perf_counter() - clock, 3)
                raw_path = raw_dir / f"{case['case_id']}.json"
                _write_json(raw_path, report)
                normalized = normalize_observations(report)
                result = evaluate_case({
                    "case_id": case["case_id"],
                    "case_title": case["title"],
                    "expected_observations": case["expectations"],
                }, report)
                accuracy_results.append(result)
                _write_json(
                    accuracy_cases / f"{case['case_id']}.json", result.to_dict()
                )
                (accuracy_cases / f"{case['case_id']}.md").write_text(
                    _case_markdown(result), encoding="utf-8", newline="\n"
                )
                run_cases.append({
                    "case_id": case["case_id"],
                    "title": case["title"],
                    "status": "completed",
                    "analysis_started_at": case_started,
                    "analysis_completed_at": utc_now(),
                    "runtime_seconds": runtime,
                    "raw_result_path": raw_path.relative_to(root).as_posix(),
                    "expectations_hash": case["expectations_hash"],
                    "expected_metric_count": len(case["expectations"]),
                    "normalized_metric_count": len(normalized),
                    "clip_validation": validations[case["case_id"]],
                })
            except Exception as exc:
                run_cases.append({
                    "case_id": case["case_id"], "title": case["title"],
                    "status": "failed", "analysis_started_at": case_started,
                    "analysis_completed_at": utc_now(),
                    "runtime_seconds": round(time.perf_counter() - clock, 3),
                    "expectations_hash": case["expectations_hash"],
                    "reason": str(exc),
                    "clip_validation": validations[case["case_id"]],
                })
        completed_at = utc_now()
        summary = aggregate_results(run_id, accuracy_results, completed_at)
        expected_count = sum(len(item["expectations"]) for item in selected)
        template_slots = len(selected) * len(ANNOTATION_METRICS)
        coverage = {
            "annotated_metric_count": expected_count,
            "recommended_metric_slots": template_slots,
            "manual_annotation_coverage": round(
                expected_count / template_slots, 4
            ) if template_slots else 0.0,
            "evaluability_coverage": summary.evaluability_coverage,
        }
        summary_payload = {**summary.to_dict(), "manual_coverage": coverage}
        _write_json(root / "accuracy" / "summary.json", summary_payload)
        (root / "accuracy" / "summary.md").write_text(
            accuracy_markdown(summary) + _coverage_markdown(coverage),
            encoding="utf-8", newline="\n",
        )
        run = {
            "schema_version": SCHEMA_VERSION,
            "validation_version": VALIDATION_VERSION,
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "git_commit": _git_commit(),
            "manifest_path": str(manifest_path.resolve()),
            "network_access_enabled": bool(allow_network),
            "observation_pipeline_received_expectations": False,
            "coverage": coverage,
            "cases": run_cases,
        }
        _write_json(root / "run.json", run)
        return run, root


def _find_case(manifest, case_id):
    for case in manifest["cases"]:
        if case["case_id"] == case_id:
            return case
    raise ValueError(f"Unknown real-world case: {case_id}")


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )


def _git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def _percent(value):
    return "Unavailable" if value is None else f"{value * 100:.1f}%"


def _case_markdown(result):
    lines = [
        f"# Real-World Accuracy · {result.case_id}", "",
        f"- Title: {result.case_title}",
        f"- Status: {result.status}",
        f"- Weighted accuracy: {_percent(result.weighted_score)}",
        f"- Evaluability coverage: {_percent(result.evaluability_coverage)}",
        f"- Unavailable metrics: {result.unavailable_metrics}", "",
        "| Metric | Expected | Observed | Comparison | Status |",
        "|---|---|---|---|---|",
    ]
    for metric in result.evaluated_metrics:
        lines.append(
            f"| {metric.metric} | `{metric.expected}` | `{metric.observed}` | "
            f"{metric.comparison_method} | {metric.status} |"
        )
    if not result.evaluated_metrics:
        lines.append("| No expectations were annotated | — | — | — | unevaluable |")
    return "\n".join(lines) + "\n"


def _coverage_markdown(coverage):
    return (
        "\n## Manual annotation coverage\n\n"
        f"- Annotated metrics: {coverage['annotated_metric_count']}\n"
        f"- Recommended metric slots: {coverage['recommended_metric_slots']}\n"
        f"- Template coverage: {_percent(coverage['manual_annotation_coverage'])}\n"
        f"- Evaluability among annotated metrics: "
        f"{_percent(coverage['evaluability_coverage'])}\n"
    )
