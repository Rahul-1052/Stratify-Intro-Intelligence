"""Resumable wrapper around the existing production analysis path."""

import json
import subprocess
import uuid
from pathlib import Path
from datetime import datetime, timezone

from version import STRATIFY_VERSION
from .checks import run_quality_checks
from .models import ValidationCase, ValidationRun
from .pipeline_trace import PipelineTrace, classify_failure, evidence_counts


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
            trace = PipelineTrace(run_id, case_id, case.validation_kind)
            acquisition = trace.stage("acquisition")
            acquisition.transition("running")
            local_source = entry.get("local_source")
            if local_source and not Path(local_source).is_file():
                error = FileNotFoundError(local_source)
                acquisition.transition("failed", error=error)
                trace.failure_category = classify_failure(error, stage="acquisition")
            try:
                if acquisition.stage_status == "failed":
                    raise FileNotFoundError(local_source or case.source)
                report = self._analyze(entry, no_network=no_network)
                counts = evidence_counts(report)
                failed = report.get("status") == "failed"
                failed_stage = _reported_stage(report) if failed else ""
                clip = trace.stage("clip preparation")
                frame_stage = trace.stage("frame extraction")
                if failed_stage == "acquisition":
                    acquisition.transition("failed", warnings=report.get("warnings", []),
                                           error=RuntimeError(report.get("error") or "Source context was unavailable."),
                                           provenance="production report")
                    clip.transition("skipped", warnings=["Acquisition failed."])
                    frame_stage.transition("skipped", warnings=["Acquisition failed."])
                else:
                    acquisition.transition("completed_with_warnings" if report.get("warnings") else "completed",
                                           warnings=report.get("warnings", []) if failed else [],
                                           output_references=[local_source or entry.get("url", "")],
                                           provenance="production module boundary")
                    clip.transition("running")
                    clip.transition("completed" if local_source else "completed_with_warnings",
                                    warnings=[] if local_source else ["Clip preparation output is reported by the production module."],
                                    output_references=[local_source] if local_source else [],
                                    provenance="existing cached/local clip" if local_source else "production report")
                    frame_stage.transition("running")
                if failed:
                    if failed_stage == "acquisition":
                        pass
                    elif failed_stage == "frame extraction":
                        frame_stage.transition("failed", warnings=report.get("warnings", []),
                                               error=RuntimeError(report.get("error") or report.get("stage") or "analysis failed"),
                                               evidence_counts=counts, provenance="production report")
                    else:
                        frame_stage.transition("completed" if counts["sampled_frames"] else "unavailable",
                                               evidence_counts=counts, provenance="derived from production report")
                    _complete_derived_stages(trace, report, counts, failed_stage)
                    trace.failure_category = classify_failure(report=report, stage=failed_stage)
                else:
                    frame_stage.transition("completed" if counts["sampled_frames"] else "completed_with_warnings",
                                           warnings=[] if counts["sampled_frames"] else ["No explicit sampled-frame count was serialized."],
                                           evidence_counts=counts, provenance="derived from production report")
                    _complete_derived_stages(trace, report, counts)
                persistence = trace.stage("persistence")
                persistence.transition("running")
                reference = self.store.save_report(run_id, case_id, report).relative_to(self.store.root).as_posix()
                persistence.transition("completed", output_references=[reference])
                reconstruction = trace.stage("reconstruction")
                reconstruction.transition("skipped", warnings=["Validation reports are not Creator Memory normalized records."],
                                          provenance="not applicable to this validation case")
                case.analysis_status = "completed" if report.get("status") in {"success", "partial"} else report.get("status", "unknown")
                case.report_reference = reference
                case.objective_warnings = run_quality_checks(report)
                value = case.to_dict()
                value["characteristics"] = report_characteristics(report)
                value.update(_trace_case_fields(trace, counts))
                cases.append(value)
            except Exception as exc:
                active = next((item for item in trace.stages if item.stage_status == "running"), None)
                if active:
                    active.transition("failed", error=exc)
                failed_name = trace.first_failed_stage or (active.stage_name if active else "acquisition")
                trace.failure_category = trace.failure_category or classify_failure(exc, stage=failed_name)
                for stage in trace.stages:
                    if stage.stage_status == "pending":
                        stage.transition("skipped", warnings=[f"Skipped after {failed_name} failed."])
                case.analysis_status = "failed"
                case.objective_warnings = [{"code": "acquisition_or_analysis_failure", "severity": "warning",
                    "section": "acquisition", "message": str(exc), "classification": "recorded failure; requires human review"}]
                value = case.to_dict()
                value.update(_trace_case_fields(trace, {}))
                cases.append(value)
            trace_reference = self.store.save_trace(run_id, case_id, trace).relative_to(self.store.root).as_posix()
            cases[-1]["pipeline_trace_reference"] = trace_reference
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


def _reported_stage(report):
    value = " ".join((str(report.get("stage") or ""),
                      " ".join(map(str, report.get("warnings", []) or [])),
                      str(report.get("error") or ""))).lower()
    mapping = (("acqui", "acquisition"), ("clip", "clip preparation"), ("frame", "frame extraction"),
               ("temporal", "temporal observation"), ("semantic", "semantic observation"),
               ("benchmark", "benchmark discovery"), ("qualif", "evidence qualification"),
               ("reason", "creative reasoning"), ("experiment", "experiment generation"),
               ("report", "report construction"))
    if "fetch video data" in value or "youtube context" in value:
        return "acquisition"
    if "youtube_api_key" in value or "youtube api key" in value:
        return "acquisition"
    return next((stage for marker, stage in mapping if marker in value), "report construction")


def _complete_derived_stages(trace, report, counts, failed_stage=""):
    stages = ("temporal observation", "semantic observation", "benchmark discovery",
              "evidence qualification", "creative reasoning", "experiment generation",
              "report construction")
    failed_seen = failed_stage in {"acquisition", "clip preparation", "frame extraction"}
    for name in stages:
        stage = trace.stage(name)
        stage.transition("running")
        if name == failed_stage:
            stage.transition("failed", error=RuntimeError(report.get("error") or report.get("stage") or "stage failed"),
                             warnings=report.get("warnings", []), provenance="production report")
            failed_seen = True
        elif failed_seen:
            stage.transition("skipped", warnings=[f"Skipped after {failed_stage} failed."])
        else:
            available = {
                "temporal observation": counts.get("temporal_windows", 0),
                "semantic observation": bool(report.get("creative_structure") or report.get("creative_understanding")),
                "benchmark discovery": counts.get("benchmark_candidates", 0),
                "evidence qualification": counts.get("qualified_benchmarks", 0),
                "creative reasoning": bool(report.get("creative_reasoning")),
                "experiment generation": counts.get("supported_experiments", 0),
                "report construction": bool(report.get("creator_report")),
            }[name]
            status = "completed" if available else ("unavailable" if name in {"benchmark discovery", "evidence qualification"} else "completed_with_warnings")
            stage.transition(status, evidence_counts=counts,
                             warnings=[] if available else [f"No explicit {name} evidence was serialized."],
                             provenance="derived from production report")


def _trace_case_fields(trace, counts):
    return {"last_successful_stage": trace.last_successful_stage,
            "first_failed_stage": trace.first_failed_stage,
            "failure_category": trace.failure_category,
            "evidence_counts": counts}


def trace_reconstruction(run_id, case_id, record, video=None, revision=1, reconstructor=None):
    trace = PipelineTrace(run_id, case_id, "saved-report reconstruction")
    for stage in trace.stages[:-1]:
        stage.transition("skipped", warnings=["Not part of reconstruction operation."])
    stage = trace.stage("reconstruction")
    stage.transition("running")
    try:
        if reconstructor is None:
            from core.memory.reconstruction import reconstruct_creator_report
            reconstructor = reconstruct_creator_report
        result = reconstructor(record, video, revision)
        stage.transition("completed", evidence_counts={"reconstructed_reports": 1})
        return result, trace
    except Exception as exc:
        stage.transition("failed", error=exc)
        trace.failure_category = classify_failure(exc, stage="reconstruction")
        return None, trace
