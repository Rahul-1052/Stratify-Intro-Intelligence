"""Aggregate evidence availability and pipeline audit exports."""

import csv
import io
import json
from collections import Counter

DIMENSIONS = ("sampled_frames", "temporal_windows", "human_presence", "text_overlay",
              "scene_type", "visual_energy", "motion_level", "lighting", "color_feel",
              "benchmark_candidates", "qualified_benchmarks", "supported_opportunities",
              "supported_experiments")


def _flatten(value, prefix="", output=None):
    output = output if output is not None else {}
    if isinstance(value, dict):
        for key, item in value.items():
            _flatten(item, f"{prefix}.{key}" if prefix else str(key), output)
    elif isinstance(value, list):
        for item in value:
            _flatten(item, prefix, output)
    elif prefix:
        output.setdefault(prefix.lower(), []).append(value)
    return output


def case_availability(case, report):
    flat = _flatten(report)
    counts = case.get("evidence_counts") or {}
    result = {}
    aliases = {
        "human_presence": ("human_presence", "people", "face", "person"),
        "text_overlay": ("text_overlay", "text_role", "written"),
        "scene_type": ("scene_type", "setting"),
        "visual_energy": ("visual_energy",),
        "motion_level": ("motion_level", "motion"),
        "lighting": ("lighting",),
        "color_feel": ("color_feel", "color"),
    }
    for dimension in DIMENSIONS:
        if dimension in counts:
            value = counts.get(dimension, 0)
            result[dimension] = "available and qualified" if value else "unavailable"
            continue
        values = [value for key, items in flat.items()
                  if any(alias in key for alias in aliases.get(dimension, (dimension,)))
                  for value in items]
        normalized = {str(value).strip().lower() for value in values}
        if not values or normalized <= {"", "none", "unknown", "unavailable", "not observed"}:
            result[dimension] = "unavailable"
        elif normalized & {"limited", "weak", "uncertain", "isolated"}:
            result[dimension] = "available but weak"
        else:
            result[dimension] = "available and qualified"
    return result


def aggregate_evidence(run, report_loader):
    cases = []
    totals = {dimension: Counter() for dimension in DIMENSIONS}
    for case in run.get("cases", []):
        report = report_loader(case["report_reference"]) if case.get("report_reference") else {}
        availability = case_availability(case, report)
        cases.append({"case_id": case["case_id"], "availability": availability})
        for dimension, status in availability.items():
            totals[dimension][status] += 1
    return {"provenance": "real-video pipeline validation" if "real" in run.get("validation_mode", "") else run.get("validation_mode"),
            "cases": cases, "summary": {key: dict(value) for key, value in totals.items()}}


def audit_exports(run, inputs, aggregate):
    output = io.StringIO(newline="")
    fields = ("case_id", "analysis_status", "failure_category", "last_successful_stage", "first_failed_stage")
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(({key: case.get(key, "") for key in fields} for case in run.get("cases", [])))
    failures = Counter(case.get("failure_category") or "none" for case in run.get("cases", []))
    lines = [f"# Real Pipeline Reliability and Evidence Audit — {run.get('run_id')}", "",
             "## Inputs discovered", "", f"- Reproducible pilot inputs selected: {len(inputs)}",
             "- Creator, title, niche, and URL metadata were not inferred from filenames.", "",
             "## Cases attempted", "", f"- Attempted: {len(run.get('cases', []))}",
             f"- Successful reports: {sum(c.get('analysis_status') == 'completed' for c in run.get('cases', []))}",
             f"- Failed reports: {sum(c.get('analysis_status') == 'failed' for c in run.get('cases', []))}", "",
             "## Failure categories", *[f"- {key}: {value}" for key, value in failures.items()], "",
             "## Per-case stages", *[f"- {c.get('case_id')}: last successful `{c.get('last_successful_stage') or 'none'}`; first failed `{c.get('first_failed_stage') or 'none'}`; persistence `{_stage(c, 'persistence')}`; reconstruction `{_stage(c, 'reconstruction')}`" for c in run.get("cases", [])],
             "", "## Evidence availability", "",
             *[f"- {key}: {json.dumps(value)}" for key, value in aggregate.get("summary", {}).items()],
             "", "## Recurring infrastructure problems", "",
             *[f"- {key}: {value}" for key, value in failures.items() if key != "none" and value > 1],
             "", "## Limitations", "",
             "- Stage evidence outside persistence is derived from the unchanged production report boundary unless marked direct.",
             "- Cached clips lack verified creator, title, niche, and source URL provenance.",
             "- An unavailable serialized count does not prove the stage performed no internal work.", "",
             "## Recommended next investigation", "",
             "- Inspect the first failed stage and preserved Builder error details before changing production behavior."]
    return {"aggregate_evidence_availability.json": json.dumps(aggregate, indent=2),
            "failure_summary.csv": output.getvalue(), "pipeline_audit.md": "\n".join(lines)}


def _stage(case, name):
    trace = case.get("pipeline_trace") or {}
    return next((stage.get("stage_status") for stage in trace.get("stages", []) if stage.get("stage_name") == name), "see trace JSON")
