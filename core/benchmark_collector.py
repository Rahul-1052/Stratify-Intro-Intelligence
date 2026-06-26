import re

from core.youtube_client import search_videos
from core.benchmark_cleaner import clean_benchmark_videos


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

    overlap = query_words.intersection(title_words)
    return len(overlap)


def _score_query_results(videos, query):
    if not videos:
        return 0

    score = 0

    for video in videos:
        score += _score_video_against_query(video, query)

    return score


def _select_lower_performers(sorted_by_views, top_performers):
    top_ids = {video.get("video_id") for video in top_performers}

    top_channels = {
        video.get("channel_id") or video.get("channel_title")
        for video in top_performers
        if video.get("channel_id") or video.get("channel_title")
    }

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
        and (
            not (video.get("channel_id") or video.get("channel_title"))
            or (video.get("channel_id") or video.get("channel_title")) not in top_channels
        )
    ]

    if len(strict_lower_pool) >= 3:
        return (
            sorted(strict_lower_pool, key=lambda video: video.get("views", 0))[:5],
            "Selected relevant lower-view videos with channel separation and a meaningful view gap.",
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

    return (
        [],
        "Not enough relevant benchmark candidates to select a lower-performer set.",
    )


def collect_benchmark_videos(category, user_video_id=None, max_results=15):
    candidate_queries = category.get("candidate_queries", [])

    if not candidate_queries:
        fallback = category.get("search_query", "")
        candidate_queries = [fallback] if fallback else []

    if not candidate_queries:
        return {
            "query": "",
            "benchmark_anchor": "",
            "query_scores": {},
            "candidate_count": 0,
            "cleaned_count": 0,
            "lower_performer_reason": "No candidate queries were available.",
            "top_performers": [],
            "lower_performers": [],
            "all_candidates": [],
        }

    query_results = {}
    query_scores = {}

    for query in candidate_queries[:5]:
        results = search_videos(
            query=query,
            max_results=max_results,
            order="relevance",
        )

        filtered_results = []

        for video in results:
            if user_video_id and video.get("video_id") == user_video_id:
                continue

            if video.get("views", 0) <= 0:
                continue

            video["matched_query"] = query
            filtered_results.append(video)

        query_results[query] = filtered_results
        query_scores[query] = _score_query_results(filtered_results, query)

    best_query = max(query_scores, key=query_scores.get)
    best_results = query_results.get(best_query, [])

    cleaned = clean_benchmark_videos(
        best_results,
        source_terms=best_query.split(),
        title_parts=[best_query],
    )

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
        "candidate_count": len(best_results),
        "cleaned_count": len(sorted_by_views),
        "lower_performer_reason": lower_performer_reason,
        "search_queries_used": candidate_queries[:5],
        "top_performers": top_performers,
        "lower_performers": lower_performers,
        "all_candidates": sorted_by_views,
    }