import math
import re
from collections import Counter

from core.benchmark_signature import (
    build_benchmark_signature,
    compare_benchmark_signatures,
    minimum_signature_compatibility,
)


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


def _tokens(text):
    return _normalize(text).split()


def _unique_tokens(text):
    return set(_tokens(text))


def _build_query_profile(
    source_terms=None,
    title_parts=None,
):
    queries = []

    for item in source_terms or []:
        if item:
            queries.append(str(item))

    for item in title_parts or []:
        if item:
            queries.append(str(item))

    query_token_sets = [
        _unique_tokens(query)
        for query in queries
        if query
    ]

    document_frequency = Counter()

    for token_set in query_token_sets:
        for token in token_set:
            document_frequency[token] += 1

    query_count = max(
        len(query_token_sets),
        1,
    )

    token_weights = {}

    for token, frequency in document_frequency.items():
        specificity = (
            math.log(
                (query_count + 1)
                / (frequency + 1)
            )
            + 1
        )

        token_weights[token] = round(
            specificity,
            4,
        )

    return {
        "queries": queries,
        "query_count": query_count,
        "token_weights": token_weights,
    }


def _phrase_score(
    title,
    queries,
):
    normalized_title = _normalize(title)
    title_words = normalized_title.split()

    score = 0.0

    for query in queries:
        normalized_query = _normalize(query)
        query_words = _tokens(query)

        if not query_words:
            continue

        if (
            normalized_query
            and normalized_query in normalized_title
        ):
            score += len(query_words)
            continue

        matched_words = [
            word
            for word in query_words
            if word in title_words
        ]

        if matched_words:
            score += (
                len(matched_words)
                / len(query_words)
            )

    return score


def _anchor_score(
    title,
    token_weights,
):
    title_tokens = _unique_tokens(title)

    return sum(
        weight
        for token, weight
        in token_weights.items()
        if token in title_tokens
    )


def _matched_query_score(video):
    matched_query = video.get(
        "matched_query",
        "",
    )

    title = video.get(
        "title",
        "",
    )

    if not matched_query:
        return 0.0

    query_tokens = _unique_tokens(
        matched_query
    )

    title_tokens = _unique_tokens(title)

    if not query_tokens or not title_tokens:
        return 0.0

    overlap = query_tokens.intersection(
        title_tokens
    )

    return (
        len(overlap)
        / max(len(query_tokens), 1)
    )


def _raw_relevance_score(
    video,
    profile,
):
    title = video.get(
        "title",
        "",
    )

    anchor_score = _anchor_score(
        title,
        profile["token_weights"],
    )

    phrase_score = _phrase_score(
        title,
        profile["queries"],
    )

    matched_query_score = (
        _matched_query_score(video)
    )

    return round(
        anchor_score
        + phrase_score
        + matched_query_score,
        4,
    )


def _normalized_topic_score(
    video,
    profile,
):
    raw_score = _raw_relevance_score(
        video,
        profile,
    )

    if raw_score <= 0:
        return 0.0

    return round(
        1.0 - math.exp(
            -raw_score / 5.0
        ),
        4,
    )


def _dedupe(scored):
    seen_ids = set()
    seen_titles = set()
    seen_channels = {}

    cleaned = []

    for video in scored:
        video_id = video.get(
            "video_id"
        )

        title = video.get(
            "title",
            "",
        )

        channel = video.get(
            "channel_title",
            "",
        )

        normalized_title = _normalize(
            title
        )[:120]

        normalized_channel = _normalize(
            channel
        )

        if video_id in seen_ids:
            continue

        if (
            normalized_title
            and normalized_title in seen_titles
        ):
            continue

        if (
            normalized_channel
            and seen_channels.get(
                normalized_channel,
                0,
            ) >= 2
        ):
            continue

        seen_ids.add(video_id)

        if normalized_title:
            seen_titles.add(
                normalized_title
            )

        if normalized_channel:
            seen_channels[
                normalized_channel
            ] = (
                seen_channels.get(
                    normalized_channel,
                    0,
                )
                + 1
            )

        cleaned.append(video)

    return cleaned


def _candidate_context(video):
    """
    Candidate observations may be attached later by the
    benchmark intro pipeline.

    Metadata-only candidates remain valid but receive limited
    evidence coverage.
    """

    return {
        "vision": (
            video.get("vision")
            or video.get("intro_observation")
            or video.get("observation")
            or {}
        ),
        "understanding": (
            video.get("understanding")
            or video.get("intro_understanding")
            or {}
        ),
    }


def clean_benchmark_videos(
    videos,
    source_terms=None,
    title_parts=None,
    user_video=None,
    user_signature=None,
    user_vision=None,
    user_understanding=None,
):
    """
    Rank benchmark candidates using neutral evidence comparison.

    No content categories, predefined format labels, keyword
    blacklists, or hand-written format conflicts are used.
    """

    profile = _build_query_profile(
        source_terms=source_terms,
        title_parts=title_parts,
    )

    if user_signature is None:
        user_signature = build_benchmark_signature(
            video=user_video or {},
            vision=user_vision or {},
            understanding=user_understanding or {},
        )

    compatibility_gate = (
        minimum_signature_compatibility(
            user_signature
        )
    )

    scored = []

    for video in videos or []:
        video_id = video.get(
            "video_id"
        )

        title = video.get(
            "title",
            "",
        )

        if not video_id or not title:
            continue

        raw_relevance = _raw_relevance_score(
            video,
            profile,
        )

        topic_score = _normalized_topic_score(
            video,
            profile,
        )

        candidate_context = _candidate_context(
            video
        )

        candidate_signature = (
            build_benchmark_signature(
                video=video,
                vision=candidate_context["vision"],
                understanding=(
                    candidate_context["understanding"]
                ),
            )
        )

        comparison = compare_benchmark_signatures(
            reference=user_signature,
            candidate=candidate_signature,
            topic_score=topic_score,
        )

        item = dict(video)

        item[
            "benchmark_relevance_score"
        ] = raw_relevance

        item[
            "benchmark_topic_score"
        ] = topic_score

        item[
            "benchmark_signature"
        ] = candidate_signature

        item[
            "benchmark_compatibility"
        ] = comparison

        item[
            "benchmark_compatibility_score"
        ] = comparison[
            "compatibility_score"
        ]

        item[
            "benchmark_evidence_coverage"
        ] = comparison[
            "evidence_coverage"
        ]

        item[
            "benchmark_confidence"
        ] = comparison[
            "confidence"
        ]

        # Apply strict rejection only when both intros
        # have actually been observed.
        #
        # Metadata-only search candidates are ranked,
        # but they are not falsely treated as fully understood.
        if (
            comparison["both_intros_observed"]
            and comparison[
                "compatibility_score"
            ] < compatibility_gate
        ):
            continue

        scored.append(item)

    scored.sort(
        key=lambda item: (
            item.get(
                "benchmark_compatibility_score",
                0,
            ),
            item.get(
                "benchmark_evidence_coverage",
                0,
            ),
            item.get(
                "benchmark_topic_score",
                0,
            ),
            item.get(
                "views",
                0,
            ),
        ),
        reverse=True,
    )

    return _dedupe(scored)