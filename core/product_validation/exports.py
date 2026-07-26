"""Portable validation exports with review provenance."""

import csv
import io
import json
from collections import Counter

from .checks import issue_signature


def summarize(run):
    cases = run.get("cases", [])
    decisions = Counter(case.get("decision", "requires human review") for case in cases)
    warnings = sum(len(case.get("objective_warnings", [])) for case in cases)
    issues = [issue for case in cases for issue in case.get("issues", [])]
    recurring = Counter(issue_signature(issue) for issue in issues)
    return {"cases": len(cases), "completed_analyses": sum(c.get("analysis_status") == "completed" for c in cases),
            "failures": sum(c.get("analysis_status") == "failed" for c in cases),
            "pending_reviews": sum(c.get("reviewer_status") != "reviewed" for c in cases),
            "objective_warnings": warnings, "decisions": dict(decisions),
            "niches": dict(Counter(c.get("niche", "unknown") for c in cases)),
            "experiment_counts": dict(Counter(str(c.get("characteristics", {}).get("experiment_count", 0)) for c in cases)),
            "recurring_issues": {key: count for key, count in recurring.items() if key and count > 1},
            "review_provenance": "Human findings include only cases explicitly marked reviewed."}


def _csv(rows, fields):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def export_bundle(run):
    reviews = [{"case_id": c.get("case_id"), "reviewer_status": c.get("reviewer_status"),
                "decision": c.get("decision"), "one_change": c.get("one_change"), **(c.get("score") or {})} for c in run.get("cases", [])]
    issues = [{**i, "case_id": c.get("case_id")} for c in run.get("cases", []) for i in c.get("issues", [])]
    summary = summarize(run)
    md = [f"# Product Validation — {run.get('run_id')}", "", f"Validation mode: **{run.get('validation_mode')}**",
          "", "> Automated warnings are heuristic review, not creator validation or confirmed defects.", "",
          "## Run overview", "", *(f"- {k.replace('_',' ').title()}: {v}" for k, v in summary.items()), "",
          "## Limitations", "", "- Subjective scores remain pending until a human saves a review.",
          "- Fixture results are not real-video pipeline validation or creator interview feedback.", "",
          "## Recommended next investigations", "", "- Review recurring warnings and confirm them against report evidence."]
    return {"run.json": json.dumps(run, indent=2, ensure_ascii=False),
            "human_reviews.csv": _csv(reviews, list(reviews[0]) if reviews else ["case_id"]),
            "issues.csv": _csv(issues, list(issues[0]) if issues else ["case_id"]),
            "summary.json": json.dumps(summary, indent=2, ensure_ascii=False),
            "validation_report.md": "\n".join(md)}
