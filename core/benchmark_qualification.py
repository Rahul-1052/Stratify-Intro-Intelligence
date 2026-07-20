"""Post-observation benchmark qualification and performance grouping.

Compatibility and performance are deliberately independent. Candidates first
qualify for the same evidence-inferred viewing job; only that neighborhood is
split into stronger and lower performance groups.
"""

from typing import Any, Dict, Mapping, Sequence, Tuple

from core.benchmark_signature import build_benchmark_signature, compare_benchmark_signatures
from core.viewer_job_comparison import compare_viewer_jobs
from core.benchmark_intelligence_v2 import assess_benchmark_quality, select_performance_cohorts


MIN_QUALIFIED_CANDIDATES = 4
MIN_GROUP_SIZE = 2


def qualify_observed_benchmarks(
    user_video: Mapping[str, Any],
    user_vision: Mapping[str, Any],
    user_understanding: Mapping[str, Any],
    user_features: Mapping[str, Any],
    observed_candidates: Sequence[Mapping[str, Any]],
    user_content_identity: Mapping[str, Any] = None,
) -> Dict[str, Any]:
    user_identity = build_benchmark_signature(
        video=user_video,
        vision=user_vision,
        understanding=user_understanding,
        features=user_features,
        content_identity=user_content_identity or {},
    )
    diagnostics = []
    qualified = []

    for result in observed_candidates or []:
        video = dict(result.get("video") or {})
        observed = result.get("status") == "success"
        metadata_comparison = dict(video.get("benchmark_compatibility") or {})
        diagnostic = {
            "video_id": video.get("video_id", ""),
            "title": video.get("title", ""),
            "channel_title": video.get("channel_title", ""),
            "evidence_mode": "fully_observed" if observed else "metadata_only",
            "metadata_compatibility": metadata_comparison.get(
                "metadata_compatibility",
                metadata_comparison.get("compatibility_score", 0.0),
            ),
            "observed_intro_compatibility": 0.0,
            "viewer_job_compatibility": 0.0,
            "evidence_coverage": metadata_comparison.get("evidence_coverage", 0.0),
            "compatibility_confidence": metadata_comparison.get("confidence", "limited"),
            "qualification_status": "rejected",
            "rejection_reason": "Candidate intro could not be observed.",
            "performance": _performance_evidence(video),
            "content_identity": dict(result.get("content_identity") or {}),
        }

        if observed:
            candidate_identity = build_benchmark_signature(
                video=video,
                vision=result.get("vision") or {},
                understanding=result.get("understanding") or {},
                features=result.get("features") or {},
                content_identity=result.get("content_identity") or {},
            )
            comparison = compare_benchmark_signatures(user_identity, candidate_identity)
            viewer_job = compare_viewer_jobs(
                user_content_identity or {},
                result.get("content_identity") or {},
            )
            diagnostic.update(
                {
                    "metadata_compatibility": comparison["metadata_compatibility"],
                    "observed_intro_compatibility": comparison["observed_intro_compatibility"],
                    "viewer_job_compatibility": comparison["viewer_job_compatibility"],
                    "evidence_coverage": comparison["evidence_coverage"],
                    "compatibility_confidence": comparison["confidence"],
                    "compatibility_components": comparison["components"],
                    "viewer_job_assessment": viewer_job,
                }
            )
            accepted, reason = _qualification_decision(comparison, viewer_job)
            diagnostic["qualification_status"] = "qualified" if accepted else "rejected"
            diagnostic["rejection_reason"] = "" if accepted else reason
            if accepted:
                qualified.append((result, comparison, diagnostic))

        diagnostics.append(diagnostic)

    # Viewer-job qualification remains the hard evidence gate. V2 only changes
    # how that coherent neighborhood is split by performance and diversity.
    flat_videos = [dict(item[0].get("video") or {}) for item in qualified]
    top_videos, lower_videos, performance = select_performance_cohorts(flat_videos)
    if not top_videos and len(qualified) >= MIN_QUALIFIED_CANDIDATES:
        legacy_top, legacy_lower, legacy_reason = _form_coherent_performance_groups(qualified)
        top_videos = [dict(item.get("video") or {}) for item in legacy_top]
        lower_videos = [dict(item.get("video") or {}) for item in legacy_lower]
        performance.update({
            "selection_method": "backward_compatible_small_group_fallback",
            "fallback_reason": legacy_reason,
        })
    result_by_id = {item[0].get("video", {}).get("video_id"): item[0] for item in qualified}
    top_results = [result_by_id[item.get("video_id")] for item in top_videos]
    lower_results = [result_by_id[item.get("video_id")] for item in lower_videos]
    group_reason = performance.get("fallback_reason") or (
        "Final groups were formed after observed viewer-job qualification using a "
        "log-view performance gap with channel diversity."
    )
    coherent = bool(top_results and lower_results)
    qualified_channels = {
        item.get("channel_title") for item in flat_videos if item.get("channel_title")
    }
    performance.update({
        "channel_coverage": len(qualified_channels),
        "query_coverage": sorted({q for item in flat_videos for q in item.get("matched_queries", [])}),
        "benchmark_quality_warnings": [],
    })
    quality = assess_benchmark_quality(
        flat_videos, top_videos, lower_videos, performance,
        observation_ratio=(len(flat_videos) / max(len(diagnostics), 1)),
    )

    selected_ids = {
        item.get("video", {}).get("video_id")
        for item in top_results + lower_results
    }
    for diagnostic in diagnostics:
        if diagnostic["video_id"] in selected_ids:
            diagnostic["qualification_status"] = "selected"
        elif diagnostic["qualification_status"] == "qualified":
            diagnostic["qualification_status"] = "qualified_not_selected"

    return {
        "status": "success" if coherent else "limited",
        "coherent_neighborhood": coherent,
        "reason": group_reason,
        "user_identity": user_identity,
        "user_content_identity": dict(user_content_identity or {}),
        "observed_candidate_count": sum(
            item["evidence_mode"] == "fully_observed" for item in diagnostics
        ),
        "qualified_candidate_count": sum(
            item["qualification_status"] in {"selected", "qualified_not_selected"}
            for item in diagnostics
        ),
        "top_performers": top_results,
        "lower_performers": lower_results,
        "diagnostics": diagnostics,
        "performance_diagnostics": performance,
        "benchmark_quality": quality,
        "eligible_for_directional_learning": quality["eligible_for_directional_learning"],
    }


def _qualification_decision(
    comparison: Mapping[str, Any],
    viewer_job: Mapping[str, Any],
) -> Tuple[bool, str]:
    if not comparison.get("both_intros_observed"):
        return False, "Both user and candidate intros must contain observed frame evidence."
    if comparison.get("evidence_coverage", 0.0) < 0.48:
        return False, "Observed evidence coverage is too limited for qualification."
    if viewer_job.get("status") != "success":
        return False, viewer_job.get("reason") or "Viewer-job comparison was unavailable."
    if not viewer_job.get("same_viewing_job"):
        return False, viewer_job.get("reason") or "Semantic evidence does not support the same viewing job."
    viewer_intent_score = viewer_job.get("viewer_intent_score", 0.0)
    core_dimensions = (
        viewer_intent_score,
        viewer_job.get("promised_outcome_score", viewer_intent_score),
        viewer_job.get("storytelling_job_score", 0.0),
    )
    if min(core_dimensions) < 0.70:
        return False, (
            "Core viewer-job dimension floor was not met "
            f"(intent={core_dimensions[0]:.2f}, "
            f"outcome={core_dimensions[1]:.2f}, "
            f"storytelling={core_dimensions[2]:.2f}); all must be at least 0.70."
        )
    if viewer_job.get("confidence") not in {"moderate", "high", "strong"}:
        return False, "Core viewer-job compatibility did not reach usable confidence."
    if comparison.get("observed_intro_compatibility", 0.0) < 0.42:
        return False, "Observed intro behavior is not compatible enough with the user video."
    return True, ""


def _form_performance_groups(qualified):
    if len(qualified) < MIN_QUALIFIED_CANDIDATES:
        return [], [], (
            f"Only {len(qualified)} fully observed candidates qualified; "
            f"at least {MIN_QUALIFIED_CANDIDATES} are required for coherent comparison groups."
        )

    ranked = sorted(qualified, key=lambda item: item[0].get("video", {}).get("views", 0))
    group_size = min(3, len(ranked) // 2)
    if group_size < MIN_GROUP_SIZE:
        return [], [], "The qualified neighborhood is too small to form both groups."

    lower = [item[0] for item in ranked[:group_size]]
    top = [item[0] for item in ranked[-group_size:]][::-1]
    lower_max = max(item.get("video", {}).get("views", 0) for item in lower)
    top_min = min(item.get("video", {}).get("views", 0) for item in top)
    if top_min <= lower_max:
        return [], [], "Qualified candidates did not contain a separable performance contrast."

    return top, lower, (
        "Final groups were formed only after observed viewer-job qualification; "
        "raw views are retained as a separate, limited-confidence performance signal."
    )


def _form_coherent_performance_groups(qualified):
    """Form groups only when selected candidates are mutually viewer-job coherent."""
    remaining = list(qualified)
    pair_cache = {}
    while True:
        top, lower, reason = _form_performance_groups(remaining)
        if not top or not lower:
            return top, lower, reason

        selected_ids = {
            item.get("video", {}).get("video_id") for item in top + lower
        }
        selected = [
            item for item in remaining
            if item[0].get("video", {}).get("video_id") in selected_ids
        ]
        conflicts = {id(item): 0 for item in selected}
        for index, left in enumerate(selected):
            for right in selected[index + 1:]:
                left_id = left[0].get("video", {}).get("video_id", "")
                right_id = right[0].get("video", {}).get("video_id", "")
                cache_key = tuple(sorted((left_id, right_id)))
                assessment = pair_cache.get(cache_key)
                if assessment is None:
                    assessment = compare_viewer_jobs(
                        left[0].get("content_identity", {}),
                        right[0].get("content_identity", {}),
                    )
                    pair_cache[cache_key] = assessment
                if assessment.get("status") != "success" or not assessment.get(
                    "same_viewing_job"
                ):
                    conflicts[id(left)] += 1
                    conflicts[id(right)] += 1

        if not any(conflicts.values()):
            return top, lower, reason

        rejected = max(
            selected,
            key=lambda item: (
                conflicts[id(item)],
                -float(
                    item[2].get("viewer_job_assessment", {}).get(
                        "core_compatibility", 0.0
                    )
                ),
            ),
        )
        rejected[2]["qualification_status"] = "rejected"
        rejected[2]["rejection_reason"] = (
            "Candidate was individually compatible with the user video but was "
            "not mutually compatible with the selected viewer-job neighborhood."
        )
        remaining.remove(rejected)


def _performance_evidence(video):
    return {
        "metric": "raw_views",
        "value": max(int(video.get("views") or 0), 0),
        "confidence": "limited",
        "limitations": "Not normalized for publish age, impressions, or channel audience size.",
    }
