"""Golden-dataset manifest validation and local pipeline runner."""

import csv
import json
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from core.product_validation.checks import run_quality_checks


REQUIRED = {
    "case_id", "source_type", "creator_style", "content_category",
    "intro_duration", "known_visual_characteristics",
    "expected_evidence_availability", "expected_recommendation_state",
    "notes", "enabled", "provenance", "licensing_usage_note",
}


def load_golden_manifest(path):
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload.get("cases"), list):
        raise ValueError("Manifest cases must be a list.")
    seen = set()
    cases = []
    for index, raw in enumerate(payload["cases"]):
        missing = REQUIRED.difference(raw)
        if missing:
            raise ValueError(f"Case {index + 1} is missing: {', '.join(sorted(missing))}")
        case_id = str(raw["case_id"]).strip()
        if not case_id or case_id in seen:
            raise ValueError(f"Duplicate or empty case ID: {case_id}")
        seen.add(case_id)
        if not isinstance(raw["enabled"], bool):
            raise ValueError(f"{case_id}: enabled must be boolean.")
        if not isinstance(raw["known_visual_characteristics"], list):
            raise ValueError(f"{case_id}: known_visual_characteristics must be a list.")
        if not raw.get("local_clip_path") and not raw.get("youtube_url"):
            raw = {**raw, "local_clip_path": ""}
        raw["_manifest_dir"] = str(source.parent)
        cases.append(raw)
    return {"schema_version": payload.get("schema_version", 1), "cases": cases}


def evidence_coverage(report):
    intelligence = report.get("intelligence_v3") or {}
    findings = intelligence.get("findings") or []
    qualified = [
        item for item in findings
        if isinstance(item, dict)
        and item.get("availability_state") == "available_and_qualified"
    ]
    return {
        "sampled_frames": len((report.get("vision") or {}).get("frame_observations") or []),
        "finding_count": len(findings),
        "qualified_finding_count": len(qualified),
        "temporal_event_count": len(intelligence.get("meaningful_change_events") or []),
    }


def compare_runs(current, prior):
    prior_cases = {item["case_id"]: item for item in (prior or {}).get("cases", [])}
    changes = []
    for item in current.get("cases", []):
        previous = prior_cases.get(item["case_id"])
        if not previous:
            changes.append({"case_id": item["case_id"], "state": "new"})
            continue
        fields = ("status", "recommendation_state", "warning_count")
        difference = {
            key: {"prior": previous.get(key), "current": item.get(key)}
            for key in fields if previous.get(key) != item.get(key)
        }
        changes.append({
            "case_id": item["case_id"],
            "state": "changed" if difference else "unchanged",
            "differences": difference,
        })
    return changes


class GoldenDatasetRunner:
    def __init__(self, analyzer=None):
        self.analyzer = analyzer or self._default_analyzer

    @staticmethod
    def _default_analyzer(case, clip):
        from stratify_platform.module_registry import run_module
        return run_module(
            "intro_intelligence", url=case.get("youtube_url", ""),
            intro_seconds=int(case.get("intro_duration") or 15), frame_fps=1,
            uploaded_video_path=str(clip), local_source_type="uploaded_file",
            no_network=bool(case.get("_no_network")),
        )

    def run(self, cases, output_dir, no_network=False, compare_run=None):
        root = Path(output_dir)
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        run_dir = root / run_id
        (run_dir / "reports").mkdir(parents=True, exist_ok=True)
        (run_dir / "traces").mkdir(parents=True, exist_ok=True)
        results = []
        for case in cases:
            if not case.get("enabled", True):
                continue
            clip_value = case.get("local_clip_path") or ""
            clip = Path(case["_manifest_dir"]) / clip_value if clip_value else None
            if clip is None or not clip.is_file():
                reason = (
                    "Local clip is missing."
                    if not case.get("youtube_url")
                    else "Network source skipped in no-network mode."
                    if no_network else "Local clip is missing; network acquisition is not automatic."
                )
                results.append({
                    "case_id": case["case_id"], "status": "skipped",
                    "reason": reason, "runtime_seconds": 0,
                })
                continue
            started = time.perf_counter()
            try:
                report = self.analyzer({**case, "_no_network": no_network}, clip)
                runtime = round(time.perf_counter() - started, 3)
                creator = report.get("creator_report") or {}
                supported = bool((creator.get("biggest_opportunity") or {}).get("supported"))
                warnings = run_quality_checks(report)
                report_path = run_dir / "reports" / f"{case['case_id']}.json"
                report_path.write_text(
                    json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                trace = {
                    "case_id": case["case_id"], "runtime_seconds": runtime,
                    "evidence_coverage": evidence_coverage(report),
                    "confidence_breakdown": creator.get("confidence_breakdown") or {},
                    "product_validation_warnings": warnings,
                }
                trace_path = run_dir / "traces" / f"{case['case_id']}.json"
                trace_path.write_text(
                    json.dumps(trace, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                results.append({
                    "case_id": case["case_id"],
                    "status": "completed" if report.get("status") != "failed" else "failed",
                    "runtime_seconds": runtime,
                    "recommendation_state": "experiment" if supported else "abstention",
                    "warning_count": len(warnings),
                    "evidence_coverage": trace["evidence_coverage"],
                    "confidence_breakdown": trace["confidence_breakdown"],
                    "report_path": report_path.relative_to(run_dir).as_posix(),
                    "trace_path": trace_path.relative_to(run_dir).as_posix(),
                })
            except Exception as exc:
                results.append({
                    "case_id": case["case_id"], "status": "failed",
                    "reason": str(exc), "runtime_seconds": round(time.perf_counter() - started, 3),
                })
        run = {
            "schema_version": 1, "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_commit": _git_commit(), "no_network": no_network,
            "cases": results,
        }
        prior = json.loads(Path(compare_run).read_text(encoding="utf-8")) if compare_run else None
        run["comparison"] = compare_runs(run, prior) if prior else []
        json_path = run_dir / "summary.json"
        json_path.write_text(
            json.dumps(run, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_csv(results, run_dir / "summary.csv")
        return run, run_dir


def _write_csv(records, path):
    fields = sorted({key for item in records for key in item if not isinstance(item.get(key), dict)})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or ["case_id"])
        writer.writeheader()
        for item in records:
            writer.writerow({key: item.get(key, "") for key in fields})


def _git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"
