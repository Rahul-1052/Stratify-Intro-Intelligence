"""Regression comparison between two stored evaluation runs."""


def _numeric_metric(value):
    if isinstance(value, dict) and isinstance(value.get("rate"), (int, float)):
        return value["rate"]
    return value if isinstance(value, (int, float)) else None


def compare_runs(baseline, candidate):
    before = baseline.get("metrics", {}) or {}
    after = candidate.get("metrics", {}) or {}
    comparisons = []
    lower_is_better = {"unavailable_field_rate", "benchmark_failure_rate", "average_report_generation_seconds"}
    for metric in sorted(set(before) & set(after)):
        old, new = _numeric_metric(before[metric]), _numeric_metric(after[metric])
        if old is None or new is None:
            continue
        delta = round(new - old, 4)
        improved = delta < 0 if metric in lower_is_better else delta > 0
        status = "unchanged" if delta == 0 else "improvement" if improved else "regression"
        comparisons.append({"metric": metric, "baseline": old, "candidate": new, "delta": delta, "status": status})
    return {
        "baseline_run_id": baseline.get("run_id"), "candidate_run_id": candidate.get("run_id"),
        "comparisons": comparisons,
        "improvements": [item for item in comparisons if item["status"] == "improvement"],
        "regressions": [item for item in comparisons if item["status"] == "regression"],
    }
