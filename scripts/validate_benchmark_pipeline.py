"""Run reproducible, real benchmark validation and save auditable artifacts."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUTPUT_DIR = ROOT / "validation" / "benchmark_qualification"

CASES = [
    ("entertainment", "Ocean's Eleven Robbing The Casino Warner Bros Rewind"),
    ("entertainment", "The Dark Knight interrogation scene official clip"),
    ("entertainment", "Harry Potter official movie scene clip"),
    ("gaming_sports", "Minecraft survival gameplay episode creator"),
    ("gaming_sports", "Fortnite gameplay challenge creator"),
    ("gaming_sports", "NBA game highlights official"),
    ("educational_practical", "how to edit video tutorial beginner"),
    ("educational_practical", "Python tutorial practical project"),
    ("educational_practical", "how to cook pasta tutorial"),
    ("creator_led", "day in my life creator vlog"),
    ("creator_led", "I tried a challenge creator video"),
    ("creator_led", "studio makeover creator video"),
]


def _load_local_settings():
    import tomllib

    secrets_path = ROOT / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        return
    with secrets_path.open("rb") as handle:
        values = tomllib.load(handle)
    for key, value in values.items():
        if isinstance(value, (str, int, float, bool)):
            os.environ.setdefault(str(key), str(value))


def _compact_video(video):
    return {
        key: video.get(key)
        for key in (
            "video_id", "title", "channel_title", "views", "duration",
            "matched_query", "benchmark_topic_score",
            "benchmark_compatibility_score", "benchmark_evidence_coverage",
        )
        if video.get(key) is not None
    }


def _compact_report(case, source_video, report):
    benchmark = report.get("benchmark", {})
    qualification = benchmark.get("qualification", {})
    observed = benchmark.get("observed_candidates", [])
    return {
        "case": case,
        "source_video": _compact_video(source_video),
        "report_status": report.get("status"),
        "warnings": report.get("warnings", []),
        "generated_queries": benchmark.get("search_queries_used", []),
        "query_scores": benchmark.get("query_scores", {}),
        "raw_candidate_pool": [
            _compact_video(item) for item in benchmark.get("raw_candidates", [])
        ],
        "shortlist": [_compact_video(item) for item in benchmark.get("shortlist", [])],
        "observed_candidates": [
            {
                "video": _compact_video(item.get("video", {})),
                "status": item.get("status"),
                "stage": item.get("stage"),
                "error": item.get("error"),
            }
            for item in observed
        ],
        "qualification_status": qualification.get("status"),
        "qualification_reason": qualification.get("reason"),
        "user_content_identity": qualification.get("user_content_identity", {}),
        "evidence_coverage": {
            item.get("video_id"): item.get("evidence_coverage")
            for item in qualification.get("diagnostics", [])
        },
        "qualification_diagnostics": qualification.get("diagnostics", []),
        "final_stronger_group": [
            _compact_video(item) for item in benchmark.get("top_performers", [])
        ],
        "final_lower_group": [
            _compact_video(item) for item in benchmark.get("lower_performers", [])
        ],
        "recommendations": report.get("patterns", {}).get("recommendations", []),
        "confidence": report.get("patterns", {}).get("confidence"),
        "final_verdict": report.get("patterns", {}).get("final_verdict"),
    }


def _write_artifacts(results):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "real_validation_results.json"
    md_path = OUTPUT_DIR / "real_validation_results.md"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(results),
        "results": results,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = ["# Real Benchmark Qualification Validation", ""]
    for result in results:
        source = result["source_video"]
        lines.extend(
            [
                f"## {result['case']['group']}: {source.get('title', result['case']['query'])}",
                "",
                f"- Report status: {result.get('report_status')}",
                f"- Qualification: {result.get('qualification_status')}",
                f"- Raw candidates: {len(result.get('raw_candidate_pool', []))}",
                f"- Shortlisted: {len(result.get('shortlist', []))}",
                f"- Fully observed: {sum(item.get('status') == 'success' for item in result.get('observed_candidates', []))}",
                f"- Stronger group: {len(result.get('final_stronger_group', []))}",
                f"- Lower group: {len(result.get('final_lower_group', []))}",
                f"- Recommendations: {len(result.get('recommendations', []))}",
                f"- Final verdict: {result.get('final_verdict')}",
                f"- Runtime warnings: {len(result.get('warnings', []))}",
                f"- Reason: {result.get('qualification_reason')}",
                "",
                "### Selected stronger",
                *[f"- {item.get('title')} — {item.get('channel_title')}" for item in result.get("final_stronger_group", [])],
                "",
                "### Selected lower",
                *[f"- {item.get('title')} — {item.get('channel_title')}" for item in result.get("final_lower_group", [])],
                "",
                "### Rejections",
                *[
                    f"- {item.get('title')}: {item.get('rejection_reason')} "
                    f"(metadata={item.get('metadata_compatibility')}, observed={item.get('observed_intro_compatibility')}, "
                    f"job={item.get('viewer_job_compatibility')}, coverage={item.get('evidence_coverage')})"
                    for item in result.get("qualification_diagnostics", [])
                    if item.get("qualification_status") == "rejected"
                ],
                "",
            ]
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=len(CASES))
    args = parser.parse_args()
    _load_local_settings()

    from core.stratify_report import run_stratify_report
    from core.youtube_client import search_videos

    results = []
    existing = OUTPUT_DIR / "real_validation_results.json"
    if existing.exists():
        results = json.loads(existing.read_text(encoding="utf-8")).get("results", [])

    for index, (group, query) in enumerate(CASES[args.start:args.start + args.limit], args.start):
        results = [
            item for item in results
            if item.get("case", {}).get("index") != index
        ]
        matches = search_videos(query=query, max_results=5, order="relevance")
        if not matches:
            results.append({"case": {"index": index, "group": group, "query": query}, "error": "No source video found."})
            _write_artifacts(results)
            continue
        source = matches[0]
        url = f"https://www.youtube.com/watch?v={source['video_id']}"
        report = run_stratify_report(url, intro_seconds=15, frame_fps=1)
        results.append(
            _compact_report(
                {"index": index, "group": group, "query": query},
                source,
                report,
            )
        )
        _write_artifacts(results)


if __name__ == "__main__":
    main()
