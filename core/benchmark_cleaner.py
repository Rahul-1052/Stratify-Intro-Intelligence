import re


def _normalize(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _word_set(text):
    return set(_normalize(text).split())


def _overlap_score(title, source_terms, title_parts):
    title_words = _word_set(title)

    if not title_words:
        return 0

    source_words = set()

    for term in source_terms or []:
        source_words.update(_word_set(term))

    for part in title_parts or []:
        source_words.update(_word_set(part))

    if not source_words:
        return 0

    overlap = title_words.intersection(source_words)

    return len(overlap)


def clean_benchmark_videos(videos, source_terms=None, title_parts=None):
    seen_ids = set()
    seen_titles = set()
    seen_channels = {}

    cleaned = []

    for video in videos:
        video_id = video.get("video_id")
        title = video.get("title", "")
        channel = video.get("channel_title", "")

        if not video_id or not title:
            continue

        normalized_title = _normalize(title)
        short_title = normalized_title[:80]
        normalized_channel = _normalize(channel)

        if video_id in seen_ids:
            continue

        if short_title in seen_titles:
            continue

        if seen_channels.get(normalized_channel, 0) >= 2:
            continue

        overlap = _overlap_score(
            title,
            source_terms or [],
            title_parts or [],
        )

        if overlap == 0:
            continue

        video["benchmark_relevance_score"] = overlap

        seen_ids.add(video_id)
        seen_titles.add(short_title)
        seen_channels[normalized_channel] = seen_channels.get(normalized_channel, 0) + 1

        cleaned.append(video)

    cleaned = sorted(
        cleaned,
        key=lambda video: (
            video.get("benchmark_relevance_score", 0),
            video.get("views", 0),
        ),
        reverse=True,
    )

    return cleaned