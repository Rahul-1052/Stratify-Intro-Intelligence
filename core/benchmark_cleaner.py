import math
import re
from collections import Counter


def _normalize(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _tokens(text):
    return _normalize(text).split()


def _unique_tokens(text):
    return set(_tokens(text))


def _build_query_profile(source_terms=None, title_parts=None):
    queries = []

    for item in source_terms or []:
        if item:
            queries.append(str(item))

    for item in title_parts or []:
        if item:
            queries.append(str(item))

    query_token_sets = [_unique_tokens(query) for query in queries if query]

    document_frequency = Counter()

    for token_set in query_token_sets:
        for token in token_set:
            document_frequency[token] += 1

    query_count = max(len(query_token_sets), 1)

    token_weights = {}

    for token, frequency in document_frequency.items():
        specificity = math.log((query_count + 1) / (frequency + 1)) + 1
        length_boost = 1.2 if len(token) >= 5 else 1.0
        token_weights[token] = round(specificity * length_boost, 4)

    return {
        "queries": queries,
        "query_count": query_count,
        "token_weights": token_weights,
    }


def _phrase_score(title, queries):
    normalized_title = _normalize(title)
    score = 0.0

    for query in queries:
        normalized_query = _normalize(query)
        query_words = _tokens(query)

        if len(query_words) < 2:
            continue

        if normalized_query and normalized_query in normalized_title:
            score += len(query_words) * 2.0
            continue

        matched_words = [
            word for word in query_words
            if word in normalized_title.split()
        ]

        if len(matched_words) >= 2:
            score += len(matched_words) * 0.75

    return score


def _anchor_score(title, token_weights):
    title_tokens = _unique_tokens(title)

    return sum(
        weight
        for token, weight in token_weights.items()
        if token in title_tokens
    )


def _matched_query_score(video):
    matched_query = video.get("matched_query", "")
    title = video.get("title", "")

    if not matched_query:
        return 0.0

    query_tokens = _unique_tokens(matched_query)
    title_tokens = _unique_tokens(title)

    if not query_tokens or not title_tokens:
        return 0.0

    overlap = query_tokens.intersection(title_tokens)
    return len(overlap) / max(len(query_tokens), 1)


def _relevance_score(video, profile):
    title = video.get("title", "")

    anchor = _anchor_score(title, profile["token_weights"])
    phrase = _phrase_score(title, profile["queries"])
    matched_query = _matched_query_score(video)

    return round(anchor + phrase + matched_query, 4)


def _dynamic_threshold(scores):
    if not scores:
        return 0.0

    sorted_scores = sorted(scores, reverse=True)

    if len(sorted_scores) <= 3:
        return min(sorted_scores)

    mean_score = sum(sorted_scores) / len(sorted_scores)

    return max(1.0, mean_score * 0.45)


def clean_benchmark_videos(videos, source_terms=None, title_parts=None):
    profile = _build_query_profile(source_terms, title_parts)

    scored = []

    for video in videos or []:
        video_id = video.get("video_id")
        title = video.get("title", "")

        if not video_id or not title:
            continue

        score = _relevance_score(video, profile)

        if score <= 0:
            continue

        item = dict(video)
        item["benchmark_relevance_score"] = score
        scored.append(item)

    threshold = _dynamic_threshold([
        item["benchmark_relevance_score"]
        for item in scored
    ])

    seen_ids = set()
    seen_titles = set()
    seen_channels = {}

    cleaned = []

    for video in sorted(
        scored,
        key=lambda item: (
            item.get("benchmark_relevance_score", 0),
            item.get("views", 0),
        ),
        reverse=True,
    ):
        video_id = video.get("video_id")
        title = video.get("title", "")
        channel = video.get("channel_title", "")

        normalized_title = _normalize(title)[:80]
        normalized_channel = _normalize(channel)

        if video.get("benchmark_relevance_score", 0) < threshold:
            continue

        if video_id in seen_ids:
            continue

        if normalized_title in seen_titles:
            continue

        if seen_channels.get(normalized_channel, 0) >= 2:
            continue

        seen_ids.add(video_id)
        seen_titles.add(normalized_title)
        seen_channels[normalized_channel] = seen_channels.get(normalized_channel, 0) + 1

        cleaned.append(video)

    return cleaned