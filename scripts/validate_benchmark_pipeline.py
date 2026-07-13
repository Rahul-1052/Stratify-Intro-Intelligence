"""Run reproducible, real benchmark validation and save auditable artifacts."""

import argparse
import json
import os
import sys
import time
from collections import Counter
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


def _compact_report(
    case,
    source_video,
    report,
    source_resolution=None,
    processing_seconds=None,
):
    benchmark = report.get("benchmark", {})
    qualification = benchmark.get("qualification", {})
    observed = benchmark.get("observed_candidates", [])
    result = {
        "case": case,
        "source_video": _compact_video(source_video),
        "report_status": report.get("status"),
        "warnings": list(report.get("warnings", [])),
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
        "processing_seconds": processing_seconds,
    }
    if source_resolution:
        result["source_resolution"] = source_resolution
        if source_resolution.get("warning"):
            result["warnings"].append(source_resolution["warning"])
    return result


def _resolve_source(search_videos, query, previous=None):
    resolution = {"mode": "live_search", "warning": None}
    try:
        return search_videos(query=query, max_results=5, order="relevance"), resolution
    except Exception as exc:
        saved_source = (previous or {}).get("source_video", {})
        if saved_source.get("video_id"):
            return [saved_source], {
                "mode": "saved_real_source_fallback",
                "warning": f"Live source search failed: {exc}",
            }
        return [], {
            "mode": "unavailable",
            "warning": f"Live source search failed and no saved source was available: {exc}",
        }


def _write_artifacts(results):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = sorted(results, key=lambda item: item.get("case", {}).get("index", 10**9))
    json_path = OUTPUT_DIR / "real_validation_results.json"
    md_path = OUTPUT_DIR / "real_validation_results.md"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(results),
        "metrics": _calculate_metrics(results),
        "results": results,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    metrics = payload["metrics"]
    lines = [
        "# Real Benchmark Qualification Validation",
        "",
        "## Calibration Metrics",
        "",
        f"- Qualification rate: {metrics['qualification_rate']:.1%}",
        f"- Abstention rate: {metrics['abstention_rate']:.1%}",
        f"- Coherent neighborhoods: {metrics['coherent_neighborhood_count']}",
        f"- Recommendation rate: {metrics['recommendation_rate']:.1%}",
        f"- Candidate rejections: {metrics['candidate_rejection_count']}",
        f"- Average evidence coverage: {metrics['average_evidence_coverage']:.3f}",
        f"- Acquisition failures: {metrics['acquisition_failures']}",
        f"- Total processing time: {metrics['total_processing_seconds']:.1f}s",
        f"- Average processing time: {metrics['average_processing_seconds']:.1f}s",
        "",
    ]
    for result in results:
        source = result.get("source_video", {})
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


def _calculate_metrics(results):
    completed = [item for item in results if item.get("report_status") in {"success", "partial"}]
    coherent = [item for item in completed if item.get("qualification_status") == "success"]
    recommendations = [item for item in completed if item.get("recommendations")]
    diagnostics = [
        diagnostic
        for item in completed
        for diagnostic in item.get("qualification_diagnostics", [])
    ]
    coverage = [
        float(item.get("evidence_coverage") or 0.0)
        for item in diagnostics
        if item.get("evidence_mode") == "fully_observed"
    ]
    rejection_reasons = Counter(
        item.get("rejection_reason") or "unspecified"
        for item in diagnostics
        if item.get("qualification_status") == "rejected"
    )
    processing = [
        float(item["processing_seconds"])
        for item in completed
        if item.get("processing_seconds") is not None
    ]
    denominator = len(completed) or 1
    return {
        "qualification_rate": round(len(coherent) / denominator, 4),
        "abstention_rate": round((len(completed) - len(coherent)) / denominator, 4),
        "coherent_neighborhood_count": len(coherent),
        "recommendation_rate": round(len(recommendations) / denominator, 4),
        "candidate_rejection_count": sum(rejection_reasons.values()),
        "candidate_rejection_reasons": dict(rejection_reasons.most_common()),
        "average_evidence_coverage": round(sum(coverage) / len(coverage), 4) if coverage else 0.0,
        "acquisition_failures": sum(
            observed.get("status") != "success"
            for item in completed
            for observed in item.get("observed_candidates", [])
        ),
        "total_processing_seconds": round(sum(processing), 2),
        "average_processing_seconds": round(sum(processing) / len(processing), 2) if processing else 0.0,
    }


def _requalify_existing_result(result):
    from core.benchmark_qualification import (
        _form_coherent_performance_groups,
        _qualification_decision,
    )
    from core.viewer_job_comparison import compare_viewer_jobs

    started_at = time.perf_counter()
    user_identity = result.get("user_content_identity", {})
    observed_status = {
        item.get("video", {}).get("video_id"): item.get("status")
        for item in result.get("observed_candidates", [])
    }
    videos = {
        item.get("video_id"): item
        for item in result.get("shortlist", []) + result.get("raw_candidate_pool", [])
        if item.get("video_id")
    }
    qualified = []
    diagnostics = result.get("qualification_diagnostics", [])
    for diagnostic in diagnostics:
        video_id = diagnostic.get("video_id")
        if (
            diagnostic.get("evidence_mode") != "fully_observed"
            or observed_status.get(video_id) != "success"
        ):
            diagnostic["qualification_status"] = "rejected"
            diagnostic["rejection_reason"] = "Candidate intro could not be observed."
            continue

        assessment = compare_viewer_jobs(
            user_identity,
            diagnostic.get("content_identity", {}),
        )
        comparison = {
            "both_intros_observed": True,
            "evidence_coverage": diagnostic.get("evidence_coverage", 0.0),
            "observed_intro_compatibility": diagnostic.get(
                "observed_intro_compatibility", 0.0
            ),
        }
        accepted, reason = _qualification_decision(comparison, assessment)
        diagnostic["viewer_job_assessment"] = assessment
        diagnostic["viewer_job_compatibility"] = assessment.get(
            "core_compatibility", 0.0
        )
        diagnostic["qualification_status"] = "qualified" if accepted else "rejected"
        diagnostic["rejection_reason"] = "" if accepted else reason
        if accepted:
            video = dict(videos.get(video_id, {}))
            video["views"] = diagnostic.get("performance", {}).get("value", 0)
            qualified.append((
                {
                    "status": "success",
                    "video": video,
                    "content_identity": diagnostic.get("content_identity", {}),
                },
                comparison,
                diagnostic,
            ))

    stronger_results, lower_results, reason = _form_coherent_performance_groups(qualified)
    stronger = [item.get("video", {}) for item in stronger_results]
    lower = [item.get("video", {}) for item in lower_results]

    selected_ids = {
        item.get("video_id") for item in stronger + lower if item.get("video_id")
    }
    for diagnostic in diagnostics:
        if diagnostic.get("video_id") in selected_ids:
            diagnostic["qualification_status"] = "selected"
        elif diagnostic.get("qualification_status") == "qualified":
            diagnostic["qualification_status"] = "qualified_not_selected"

    coherent = bool(stronger and lower)
    result["qualification_status"] = "success" if coherent else "limited"
    result["qualification_reason"] = reason
    result["final_stronger_group"] = stronger
    result["final_lower_group"] = lower
    result["report_status"] = "success" if coherent else "partial"
    result["validation_mode"] = "persisted_real_observation_requalification"
    result["processing_seconds"] = round(time.perf_counter() - started_at, 2)
    result["recommendations"] = []
    result["final_verdict"] = (
        None
        if coherent
        else "The available benchmark evidence is too limited for a reliable directional position."
    )
    result["warnings"] = [
        warning
        for warning in result.get("warnings", [])
        if not str(warning).startswith("Benchmark qualification limited:")
    ]
    if not coherent:
        result["warnings"].append(f"Benchmark qualification limited: {reason}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=len(CASES))
    parser.add_argument(
        "--requalify-existing",
        action="store_true",
        help="Replay current qualification over persisted real observed identities.",
    )
    args = parser.parse_args()
    _load_local_settings()

    from core.stratify_report import run_stratify_report
    from core.youtube_client import search_videos

    results = []
    existing = OUTPUT_DIR / "real_validation_results.json"
    if existing.exists():
        results = json.loads(existing.read_text(encoding="utf-8")).get("results", [])

    if args.requalify_existing:
        selected_indices = set(range(args.start, args.start + args.limit))
        results = [
            _requalify_existing_result(item)
            if item.get("case", {}).get("index") in selected_indices
            else item
            for item in results
        ]
        _write_artifacts(results)
        return

    for index, (group, query) in enumerate(CASES[args.start:args.start + args.limit], args.start):
        previous = next(
            (
                item for item in results
                if item.get("case", {}).get("index") == index
            ),
            None,
        )
        matches, source_resolution = _resolve_source(search_videos, query, previous)
        if not matches:
            replacement = {
                "case": {"index": index, "group": group, "query": query},
                "source_video": {},
                "report_status": "error",
                "warnings": [source_resolution["warning"] or "No source video found."],
                "qualification_status": "limited",
                "qualification_reason": "No real source video could be resolved.",
                "source_resolution": source_resolution,
            }
            results = [
                item for item in results
                if item.get("case", {}).get("index") != index
            ]
            results.append(replacement)
            _write_artifacts(results)
            continue
        source = matches[0]
        url = f"https://www.youtube.com/watch?v={source['video_id']}"
        started_at = time.perf_counter()
        report = run_stratify_report(url, intro_seconds=15, frame_fps=1)
        processing_seconds = round(time.perf_counter() - started_at, 2)
        results = [
            item for item in results
            if item.get("case", {}).get("index") != index
        ]
        results.append(
            _compact_report(
                {"index": index, "group": group, "query": query},
                source,
                report,
                source_resolution=source_resolution,
                processing_seconds=processing_seconds,
            )
        )
        _write_artifacts(results)


if __name__ == "__main__":
    main()
