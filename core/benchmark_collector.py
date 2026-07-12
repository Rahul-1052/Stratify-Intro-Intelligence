import re
import time

from core.youtube_client import search_videos
from core.benchmark_cleaner import (
    clean_benchmark_videos,
)
from core.benchmark_signature import (
    build_benchmark_signature,
)


MAX_QUERY_ATTEMPTS = 2
QUERY_SLEEP_SECONDS = 1.0


def _normalize(text):
    text = str(text or "").lower()

    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
        flags=re.UNICODE,
    )

    text = re.sub(
        r"_+",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def _word_set(text):
    return set(
        _normalize(text).split()
    )


def _score_video_against_query(
    video,
    query,
):
    query_words = _word_set(query)

    title_words = _word_set(
        video.get("title", "")
    )

    if not query_words or not title_words:
        return 0.0

    overlap = query_words.intersection(
        title_words
    )

    return (
        len(overlap)
        / max(len(query_words), 1)
    )


def _score_query_results(
    videos,
    query,
):
    if not videos:
        return 0.0

    return sum(
        _score_video_against_query(
            video,
            query,
        )
        for video in videos
    ) / len(videos)


def _safe_search_videos(
    query,
    max_results,
):
    last_error = None

    for attempt in range(
        1,
        MAX_QUERY_ATTEMPTS + 1,
    ):
        try:
            return (
                search_videos(
                    query=query,
                    max_results=max_results,
                    order="relevance",
                ),
                None,
            )

        except Exception as exc:
            last_error = str(exc)

            if attempt < MAX_QUERY_ATTEMPTS:
                time.sleep(
                    QUERY_SLEEP_SECONDS
                )

    return [], last_error


def _dedupe_videos(videos):
    seen = set()
    deduped = []

    for video in videos or []:
        video_id = video.get(
            "video_id"
        )

        if (
            not video_id
            or video_id in seen
        ):
            continue

        seen.add(video_id)
        deduped.append(video)

    return deduped


def _select_lower_performers(
    sorted_by_views,
    top_performers,
):
    top_ids = {
        video.get("video_id")
        for video in top_performers
    }

    top_min_views = min(
        (
            video.get("views", 0)
            for video in top_performers
        ),
        default=0,
    )

    lower_view_ceiling = (
        top_min_views * 0.5
        if top_min_views
        else 0
    )

    strict_lower_pool = [
        video
        for video in sorted_by_views
        if (
            video.get("video_id")
            not in top_ids
        )
        and (
            video.get("views", 0)
            <= lower_view_ceiling
        )
    ]

    if len(strict_lower_pool) >= 3:
        return (
            sorted(
                strict_lower_pool,
                key=lambda video: (
                    video.get("views", 0)
                ),
            )[:5],
            (
                "Selected lower-view candidates "
                "from the evidence-ranked benchmark "
                "neighborhood."
            ),
        )

    fallback_lower_pool = [
        video
        for video in sorted_by_views
        if video.get("video_id")
        not in top_ids
    ]

    if len(fallback_lower_pool) >= 3:
        return (
            sorted(
                fallback_lower_pool,
                key=lambda video: (
                    video.get("views", 0)
                ),
            )[:5],
            (
                "Used the remaining evidence-ranked "
                "candidates because the strict "
                "lower-view set was too small."
            ),
        )

    return (
        [],
        (
            "Not enough evidence-ranked candidates "
            "were available for a lower-performer set."
        ),
    )


def _source_video_from_category(
    category,
):
    video = dict(
        category.get("source_video")
        or {}
    )

    field_mappings = {
        "title": "source_title",
        "description": "source_description",
        "duration": "source_duration",
        "channel_title": (
            "source_channel_title"
        ),
    }

    for target_key, source_key in (
        field_mappings.items()
    ):
        if not video.get(target_key):
            video[target_key] = category.get(
                source_key,
                "",
            )

    return video


def collect_benchmark_videos(
    category,
    user_video_id=None,
    max_results=15,
    user_video=None,
    user_vision=None,
    user_understanding=None,
    user_signature=None,
):
    """
    Backward-compatible benchmark collector.

    Existing calls continue to work:

        collect_benchmark_videos(
            category,
            user_video_id,
            max_results,
        )

    When user evidence is available, use:

        collect_benchmark_videos(
            category,
            user_video_id=video_id,
            user_video=video,
            user_vision=vision,
            user_understanding=intro_understanding,
        )
    """

    candidate_queries = list(
        category.get(
            "candidate_queries",
            [],
        )
        or []
    )

    if not candidate_queries:
        fallback_query = category.get(
            "search_query",
            "",
        )

        candidate_queries = (
            [fallback_query]
            if fallback_query
            else []
        )

    candidate_queries = [
        query
        for query in candidate_queries
        if str(query).strip()
    ][:5]

    if not candidate_queries:
        return _empty_result(
            "No candidate queries were available."
        )

    resolved_user_video = dict(
        user_video
        or _source_video_from_category(
            category
        )
        or {}
    )

    if user_signature is None:
        user_signature = (
            category.get(
                "benchmark_signature"
            )
            or build_benchmark_signature(
                video=resolved_user_video,
                vision=user_vision or {},
                understanding=(
                    user_understanding or {}
                ),
            )
        )

    query_results = {}
    query_scores = {}
    query_errors = {}
    merged_candidates = []

    for query in candidate_queries:
        results, error = _safe_search_videos(
            query=query,
            max_results=max_results,
        )

        if error:
            query_errors[query] = error

        filtered_results = []

        for video in results or []:
            if (
                user_video_id
                and video.get("video_id")
                == user_video_id
            ):
                continue

            if video.get("views", 0) <= 0:
                continue

            item = dict(video)
            item["matched_query"] = query

            filtered_results.append(item)

        query_results[query] = (
            filtered_results
        )

        query_scores[query] = (
            _score_query_results(
                filtered_results,
                query,
            )
        )

        merged_candidates.extend(
            filtered_results
        )

    merged_candidates = _dedupe_videos(
        merged_candidates
    )

    if not merged_candidates:
        result = _empty_result(
            (
                "No benchmark candidates were "
                "found from available queries."
            )
        )

        result["query_scores"] = query_scores
        result["query_errors"] = query_errors
        result["search_queries_used"] = (
            candidate_queries
        )
        result["benchmark_signature"] = (
            user_signature
        )

        return result

    best_query = max(
        query_scores,
        key=query_scores.get,
    )

    best_results = query_results.get(
        best_query,
        [],
    )

    source_terms = []
    title_parts = []

    for query in candidate_queries:
        source_terms.extend(
            str(query).split()
        )
        title_parts.append(query)

    evidence_ranked = clean_benchmark_videos(
        merged_candidates,
        source_terms=source_terms,
        title_parts=title_parts,
        user_video=resolved_user_video,
        user_signature=user_signature,
        user_vision=user_vision or {},
        user_understanding=(
            user_understanding or {}
        ),
    )

    # This is a metadata shortlist, not a benchmark group. Final stronger and
    # lower groups are forbidden until these candidates have been acquired and
    # observed against the same evidence identity as the user video.
    shortlist = evidence_ranked[:8]
    shortlist_ids = {video.get("video_id") for video in shortlist}
    metadata_diagnostics = []
    ranked_by_id = {video.get("video_id"): video for video in evidence_ranked}
    for video in merged_candidates:
        scored = ranked_by_id.get(video.get("video_id"), video)
        comparison = scored.get("benchmark_compatibility", {})
        shortlisted = video.get("video_id") in shortlist_ids
        metadata_diagnostics.append(
            {
                "video_id": video.get("video_id", ""),
                "title": video.get("title", ""),
                "channel_title": video.get("channel_title", ""),
                "metadata_compatibility": comparison.get(
                    "metadata_compatibility",
                    comparison.get("compatibility_score", 0.0),
                ),
                "evidence_coverage": comparison.get("evidence_coverage", 0.0),
                "qualification_status": "shortlisted" if shortlisted else "rejected_before_observation",
                "rejection_reason": "" if shortlisted else "Ranked outside the conservative metadata shortlist.",
                "evidence_mode": "metadata_only",
            }
        )

    observed_candidate_count = sum(
        bool(
            video.get(
                "benchmark_compatibility",
                {},
            ).get(
                "both_intros_observed"
            )
        )
        for video in evidence_ranked
    )

    benchmark_evidence_mode = (
        "observed_intro_comparison"
        if observed_candidate_count
        else "metadata_first_retrieval"
    )

    return {
        "query": best_query,
        "benchmark_anchor": best_query,
        "query_scores": query_scores,
        "query_errors": query_errors,
        "candidate_count": len(best_results),
        "merged_candidate_count": len(
            merged_candidates
        ),
        "cleaned_count": len(
            evidence_ranked
        ),
        "compatible_candidate_count": len(
            evidence_ranked
        ),
        "rejected_candidate_count": max(
            len(merged_candidates)
            - len(evidence_ranked),
            0,
        ),
        "observed_candidate_count": (
            observed_candidate_count
        ),
        "benchmark_evidence_mode": (
            benchmark_evidence_mode
        ),
        "lower_performer_reason": "Final groups await observed-intro qualification.",
        "search_queries_used": (
            candidate_queries
        ),
        "benchmark_signature": (
            user_signature
        ),
        "raw_candidates": merged_candidates,
        "shortlist": shortlist,
        "qualification_diagnostics": metadata_diagnostics,
        "top_performers": [],
        "lower_performers": [],
        "all_candidates": evidence_ranked,
    }


def _empty_result(reason):
    return {
        "query": "",
        "benchmark_anchor": "",
        "query_scores": {},
        "query_errors": {},
        "candidate_count": 0,
        "merged_candidate_count": 0,
        "cleaned_count": 0,
        "compatible_candidate_count": 0,
        "rejected_candidate_count": 0,
        "observed_candidate_count": 0,
        "benchmark_evidence_mode": (
            "unavailable"
        ),
        "lower_performer_reason": reason,
        "search_queries_used": [],
        "benchmark_signature": {},
        "top_performers": [],
        "lower_performers": [],
        "raw_candidates": [],
        "shortlist": [],
        "qualification_diagnostics": [],
        "all_candidates": [],
    }
