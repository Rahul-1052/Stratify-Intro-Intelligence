"""Portable JSON, CSV, and Markdown evaluation exports."""

import csv
import io
import json


def export_json(run):
    payload = run.to_dict() if hasattr(run, "to_dict") else run
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def export_csv(run):
    payload = run.to_dict() if hasattr(run, "to_dict") else run
    output = io.StringIO(newline="")
    fields = ["run_id", "video_id", "video_title", "category", "status", "generation_seconds", "cache_used", "field", "expected", "predicted", "agreement"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for result in payload.get("results", []):
        agreements = result.get("agreements") or [{}]
        for agreement in agreements:
            writer.writerow({
                "run_id": payload.get("run_id"), "video_id": result.get("video_id"),
                "video_title": result.get("video_title"), "category": result.get("category"),
                "status": result.get("status"), "generation_seconds": result.get("generation_seconds"),
                "cache_used": result.get("cache_used"), "field": agreement.get("field"),
                "expected": agreement.get("expected"), "predicted": agreement.get("predicted"),
                "agreement": agreement.get("result"),
            })
    return output.getvalue()


def export_markdown(run):
    payload = run.to_dict() if hasattr(run, "to_dict") else run
    metrics = payload.get("metrics", {})
    lines = [f"# Stratify Evaluation — {payload.get('run_id', 'unknown')}", "", f"Dataset: {payload.get('dataset_name', 'unknown')}", "", "## Metrics", ""]
    for key, value in metrics.items():
        lines.append(f"- **{key.replace('_', ' ').title()}**: `{json.dumps(value, ensure_ascii=False)}`")
    lines.extend(["", "## Videos", ""])
    for result in payload.get("results", []):
        lines.append(f"### {result.get('video_title', result.get('video_id'))}")
        lines.append(f"Status: **{result.get('status')}** · Category: **{result.get('category')}**")
        for agreement in result.get("agreements", []):
            lines.append(f"- {agreement.get('field')}: expected `{agreement.get('expected')}`, predicted `{agreement.get('predicted')}` — **{agreement.get('result')}**")
        lines.append("")
    return "\n".join(lines)
