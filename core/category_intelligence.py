import re


WEAK_ANCHOR_WORDS = {
    "official", "trailer", "teaser", "promo", "reaction", "reacting",
    "breakdown", "review", "explained", "analysis", "details",
    "nuevo", "nueva", "full", "video", "clip", "scene",
    "now", "playing", "super", "wiki", "hd", "4k", "8k",
    "shorts", "ytshorts", "viral", "trending"
}


def _clean_text(text):
    text = text or ""
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"[^a-zA-Z0-9\s\|\:\-\']", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clean_query(text):
    text = text or ""
    text = text.replace("´", "'").replace("`", "'").replace('"', " ")
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _remove_weak_words(query):
    words = query.split()

    strong_words = [
        word for word in words
        if word.lower() not in WEAK_ANCHOR_WORDS
    ]

    return " ".join(strong_words).strip()


def _split_title_into_candidates(title):
    clean_title = _clean_text(title)

    raw_parts = re.split(r"\||:|-", clean_title)

    candidates = []

    for part in raw_parts:
        query = _clean_query(part)
        strong_query = _remove_weak_words(query)

        if len(strong_query.split()) >= 2:
            candidates.append(strong_query)

        if len(query.split()) >= 2:
            candidates.append(query)

    full_title_query = _clean_query(clean_title)
    strong_full_title_query = _remove_weak_words(full_title_query)

    if len(strong_full_title_query.split()) >= 2:
        candidates.append(strong_full_title_query)

    if len(full_title_query.split()) >= 2:
        candidates.append(full_title_query)

    seen = set()
    unique_candidates = []

    for query in candidates:
        normalized = query.lower()

        if normalized not in seen:
            seen.add(normalized)
            unique_candidates.append(query)

    return unique_candidates[:8]


def understand_category(video):
    """
    Stratify 2.0 evidence-first query hypothesis generator.

    This does not assign fixed content categories.
    It creates multiple benchmark query hypotheses from the actual title,
    then removes weak anchor words that usually describe packaging rather
    than the content subject.

    Benchmark Collector chooses the strongest query using observed search results.
    """

    title = video.get("title", "")
    description = video.get("description", "")

    candidate_queries = _split_title_into_candidates(title)

    if not candidate_queries:
        fallback = _clean_query(title or description)
        fallback = _remove_weak_words(fallback) or fallback

        if fallback:
            candidate_queries = [fallback]

    return {
        "category": "Not pre-assigned",
        "subcategory": "Not pre-assigned",
        "micro_niche": candidate_queries[0] if candidate_queries else "",
        "search_query": candidate_queries[0] if candidate_queries else "",
        "search_queries": candidate_queries,
        "candidate_queries": candidate_queries,
        "confidence": "hypothesis_based",
        "reason": "Generated benchmark query hypotheses from title evidence without hardcoded categories.",
    }