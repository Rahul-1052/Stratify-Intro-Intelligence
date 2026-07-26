"""Resumable wrapper around the existing production analysis path."""

import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from version import STRATIFY_VERSION
from .checks import run_quality_checks
from .models import ValidationCase, ValidationRun


def report_characteristics(report):
    creator = report.get("creator_report") or {}
    opportunity = creator.get("biggest_opportunity") or {}
    confidence = creator.get("confidence_summary") or {}
    return {"report_renderable": bool(creator), "recommendation_present": bool(opportunity.get("supported")),
            "abstention_present": not bool(opportunity.get("supported")),
            "experiment_count": len(creator.get("experiments") or []),
            "benchmark_available": (report.get("benchmark_intelligence") or {}).get("status") not in {None, "unavailable", "limited"},
            "limited_evidence": report.get("status") == "partial" or "limited" in {str(v).lower() for v in confidence.values()}}


class ProductValidationRunner:
    def __init__(self, store, analyzer=None):
        self.store = store
        self.analyzer = analyzer

    def _analyze(self, entry, no_network=False):
        if "report" in entry:
            return entry["report"]
        if self.analyzer:
            return self.analyzer(entry)
        from stratify_platform.module_registry import run_module
        source = entry.get("local_source") or entry.get("url", "")
        kwargs = {"url": entry.get("url", ""), "intro_seconds": 15, "frame_fps": 1}
        if entry.get("local_source"):
            kwargs["uploaded_video_path"] = source
        if no_network and not entry.get("local_source"):
            raise RuntimeError("Network disabled and no local source is available.")
        return run_module("intro_intelligence", **kwargs)

    def run(self, entries, run_id=None, mode="fixture", resume=False, skip_existing=False,
            no_network=False, environment_notes=""):
        run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        prior = self.store.load_run(run_id) if resume and (self.store.root / "runs" / f"{run_id}.json").exists() else None
        completed = {case["case_id"]: case for case in (prior or {}).get("cases", [])}
        cases = []
        run = {"run_id": run_id, "timestamp": datetime.now(timezone.utc).isoformat(),
               "app_version": STRATIFY_VERSION, "git_commit": _git_commit(), "validation_mode": mode,
               "environment_notes": environment_notes, "cases": cases, "completed": False}
        for entry in entries:
            case_id = entry["case_id"]
            if case_id in completed and (resume or skip_existing):
                cases.append(completed[case_id])
                continue
            case = ValidationCase(case_id=case_id, source=entry.get("url") or entry.get("local_source") or "",
                                  niche=entry.get("niche", "unknown"), source_type=entry.get("source_type") or entry.get("expected_source_type", "unknown"),
                                  normalized_video_id=entry.get("normalized_video_id", ""), creator_name=entry.get("creator", ""),
                                  video_title=entry.get("title", ""), validation_kind=entry.get("validation_kind", "real-video pipeline validation"))
            try:
                report = self._analyze(entry, no_network=no_network)
                reference = self.store.save_report(run_id, case_id, report).relative_to(self.store.root).as_posix()
                case.analysis_status = "completed" if report.get("status") in {"success", "partial"} else report.get("status", "unknown")
                case.report_reference = reference
                case.objective_warnings = run_quality_checks(report)
                value = case.to_dict()
                value["characteristics"] = report_characteristics(report)
                cases.append(value)
            except Exception as exc:
                case.analysis_status = "failed"
                case.objective_warnings = [{"code": "acquisition_or_analysis_failure", "severity": "warning",
                    "section": "acquisition", "message": str(exc), "classification": "recorded failure; requires human review"}]
                cases.append(case.to_dict())
            run["cases"] = cases
            self.store.save_run(run)
        run["completed"] = True
        self.store.save_run(run)
        return run


def _git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def load_manifest(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = payload.get("cases", [])
    ids = [entry.get("case_id") for entry in entries if entry.get("enabled", True)]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate enabled case IDs are not allowed.")
    return [entry for entry in entries if entry.get("enabled", True)]
