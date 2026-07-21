"""Cache-aware execution of Intro Intelligence evaluation datasets."""

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from core.evaluation.evaluation_metrics import analyze_failures, calculate_metrics, compare_manual_labels
from core.evaluation.evaluation_models import EvaluationResult, EvaluationRun


class EvaluationRunner:
    def __init__(self, analyzer=None, output_dir="evaluation_data", dataset_store=None, clock=None):
        if analyzer is None:
            from core.stratify_report import run_stratify_report
            analyzer = run_stratify_report
        self.analyzer = analyzer
        self.output_dir = Path(output_dir)
        self.dataset_store = dataset_store
        self.clock = clock or time.perf_counter

    def _cache_path(self, video_id):
        return self.output_dir / "cache" / f"{video_id}.json"

    def _load_or_run(self, video, force):
        cache_path = self._cache_path(video.video_id)
        if cache_path.exists() and not force:
            return json.loads(cache_path.read_text(encoding="utf-8")), True, 0.0
        started = self.clock()
        report = self.analyzer(url=video.url)
        elapsed = max(self.clock() - started, 0.0)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return report, False, elapsed

    def run(self, dataset, force=False, run_id=None):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        results = []
        for video in dataset.get("videos", []):
            try:
                report, cache_used, elapsed = self._load_or_run(video, force)
                status = report.get("status", "unknown")
                agreements = compare_manual_labels(video.expected_manual_labels, report)
                result = EvaluationResult(
                    video.video_id, video.video_title, video.category, status,
                    round(elapsed, 4), report, agreements, cache_used,
                    creative_structure=report.get("creative_structure", {}) or {},
                    creative_understanding=report.get("creative_understanding", {}) or {},
                )
            except Exception as exc:
                result = EvaluationResult(video.video_id, video.video_title, video.category, "failed", 0.0, {}, [], False, str(exc))
            results.append(result)
            if self.dataset_store:
                self.dataset_store.append_history(video.video_id, {"run_id": run_id, "run_status": result.status, "evaluated_at": datetime.now(timezone.utc).isoformat(), "cache_used": result.cache_used})
        run = EvaluationRun(
            run_id=run_id, created_at=datetime.now(timezone.utc).isoformat(),
            dataset_name=dataset.get("name", "evaluation"), results=results,
            metrics=calculate_metrics(results), failure_analysis=analyze_failures(results),
        )
        path = self.output_dir / "runs" / f"{run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(run.to_dict(), indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return run


def load_runs(output_dir):
    paths = sorted((Path(output_dir) / "runs").glob("*.json"), reverse=True)
    return [json.loads(path.read_text(encoding="utf-8")) for path in paths]
