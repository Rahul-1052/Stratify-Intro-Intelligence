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

    best_query = max(
        query_scores,
        key=query_scores.get,
    )

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

    if len(sorted_by_views) >= 8:
        lower_performers = sorted_by_views[-5:]
    else:
        lower_performers = []

    return {
        "query": best_query,
        "benchmark_anchor": best_query,
        "query_scores": query_scores,
        "search_queries_used": candidate_queries[:5],
        "top_performers": top_performers,
        "lower_performers": lower_performers,
        "all_candidates": sorted_by_views,
    }