import re
import time

from core.youtube_client import search_videos
from core.benchmark_cleaner import clean_benchmark_videos


MAX_QUERY_ATTEMPTS = 2
QUERY_SLEEP_SECONDS = 1.0


def _normalize(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _word_set(text):
    return set(_normalize(text).split())


def _score_video_against_query(video, query):
    query_words = _word_set(query)
    title_words = _word_set(video.get("title", ""))

    if not query_words or not title_words:
        return 0

    return len(query_words.intersection(title_words))


def _score_query_results(videos, query):
    return sum(_score_video_against_query(video, query) for video in videos or [])


def _safe_search_videos(query, max_results):
    last_error = None

    for attempt in range(1, MAX_QUERY_ATTEMPTS + 1):
        try:
            return search_videos(
                query=query,
                max_results=max_results,
                order="relevance",
            ), None
        except Exception as exc:
            last_error = str(exc)
            if attempt < MAX_QUERY_ATTEMPTS:
                time.sleep(QUERY_SLEEP_SECONDS)

    return [], last_error


def _dedupe_videos(videos):
    seen = set()
    deduped = []

    for video in videos or []:
        video_id = video.get("video_id")
        if not video_id or video_id in seen:
            continue

        seen.add(video_id)
        deduped.append(video)

    return deduped


def _select_lower_performers(sorted_by_views, top_performers):
    top_ids = {video.get("video_id") for video in top_performers}

    top_min_views = min(
        (video.get("views", 0) for video in top_performers),
        default=0,
    )

    lower_view_ceiling = top_min_views * 0.5 if top_min_views else 0

    strict_lower_pool = [
        video
        for video in sorted_by_views
        if video.get("video_id") not in top_ids
        and video.get("views", 0) <= lower_view_ceiling
    ]

    if len(strict_lower_pool) >= 3:
        return (
            sorted(strict_lower_pool, key=lambda video: video.get("views", 0))[:5],
            "Selected relevant lower-view videos with a meaningful view gap.",
        )

    fallback_lower_pool = [
        video
        for video in sorted_by_views
        if video.get("video_id") not in top_ids
    ]

    if len(fallback_lower_pool) >= 3:
        return (
            sorted(fallback_lower_pool, key=lambda video: video.get("views", 0))[:5],
            "Used fallback lower-performer selection because strict lower set was too small.",
        )

    return [], "Not enough relevant candidates to select lower performers."


def collect_benchmark_videos(category, user_video_id=None, max_results=15):
    candidate_queries = category.get("candidate_queries", [])

    if not candidate_queries:
        fallback = category.get("search_query", "")
        candidate_queries = [fallback] if fallback else []

    candidate_queries = [query for query in candidate_queries if query]

    if not candidate_queries:
        return _empty_result("No candidate queries were available.")

    query_results = {}
    query_scores = {}
    query_errors = {}
    merged_candidates = []

    for query in candidate_queries[:5]:
        results, error = _safe_search_videos(query, max_results=max_results)

        if error:
            query_errors[query] = error

        filtered_results = []

        for video in results or []:
            if user_video_id and video.get("video_id") == user_video_id:
                continue

            if video.get("views", 0) <= 0:
                continue

            video = dict(video)
            video["matched_query"] = query
            filtered_results.append(video)

        query_results[query] = filtered_results
        query_scores[query] = _score_query_results(filtered_results, query)
        merged_candidates.extend(filtered_results)

    merged_candidates = _dedupe_videos(merged_candidates)

    if not merged_candidates:
        result = _empty_result("No benchmark candidates were found from available queries.")
        result["query_scores"] = query_scores
        result["query_errors"] = query_errors
        result["search_queries_used"] = candidate_queries[:5]
        return result

    best_query = max(query_scores, key=query_scores.get)
    best_results = query_results.get(best_query, [])

    source_terms = []
    title_parts = []

    for query in candidate_queries[:5]:
        source_terms.extend(query.split())
        title_parts.append(query)

    cleaned = clean_benchmark_videos(
        merged_candidates,
        source_terms=source_terms,
        title_parts=title_parts,
    )

    if not cleaned:
        cleaned = merged_candidates

    sorted_by_views = sorted(
        cleaned,
        key=lambda video: video.get("views", 0),
        reverse=True,
    )

    top_performers = sorted_by_views[:5]

    lower_performers, lower_performer_reason = _select_lower_performers(
        sorted_by_views,
        top_performers,
    )

    return {
        "query": best_query,
        "benchmark_anchor": best_query,
        "query_scores": query_scores,
        "query_errors": query_errors,
        "candidate_count": len(best_results),
        "merged_candidate_count": len(merged_candidates),
        "cleaned_count": len(sorted_by_views),
        "lower_performer_reason": lower_performer_reason,
        "search_queries_used": candidate_queries[:5],
        "top_performers": top_performers,
        "lower_performers": lower_performers,
        "all_candidates": sorted_by_views,
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
        "lower_performer_reason": reason,
        "search_queries_used": [],
        "top_performers": [],
        "lower_performers": [],
        "all_candidates": [],
    }