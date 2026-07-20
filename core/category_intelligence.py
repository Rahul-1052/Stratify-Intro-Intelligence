import re


WEAK_ANCHOR_WORDS = {
    "official", "trailer", "teaser", "promo", "reaction", "reacting",
    "breakdown", "review", "explained", "analysis", "details",
    "nuevo", "nueva", "full", "video", "clip", "scene",
    "now", "playing", "super", "wiki", "hd", "4k", "8k",
    "shorts", "ytshorts", "viral", "trending"
}

STOP_WORDS = {
    "a", "an", "and", "are", "at", "be", "by", "for", "from", "how",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "was", "what", "when", "where", "who", "why", "with", "you", "your",
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

    hypotheses = generate_query_hypotheses(title, description)
    candidate_queries = [item["query"] for item in hypotheses]

    if not candidate_queries:
        fallback = _clean_query(title or description)
        fallback = _remove_weak_words(fallback) or fallback

        if fallback:
            candidate_queries = [fallback]
            hypotheses = [_hypothesis(fallback, "fallback", [], "Only usable source text.")]

    return {
        "category": "Not pre-assigned",
        "subcategory": "Not pre-assigned",
        "micro_niche": candidate_queries[0] if candidate_queries else "",
        "search_query": candidate_queries[0] if candidate_queries else "",
        "search_queries": candidate_queries,
        "candidate_queries": candidate_queries,
        "query_hypotheses": hypotheses,
        "confidence": "hypothesis_based",
        "reason": "Generated benchmark query hypotheses from title evidence without hardcoded categories.",
    }


def _hypothesis(query, source, removed, rationale):
    terms = query.split()
    specificity = min(1.0, (len(set(word.lower() for word in terms)) / 6.0))
    return {
        "query": query,
        "source": source,
        "specificity": round(specificity, 3),
        "retained_terms": terms,
        "removed_weak_terms": sorted(set(removed)),
        "rationale": rationale,
    }


def generate_query_hypotheses(title, description="", limit=5):
    """Build ranked, explainable hypotheses from source text only."""
    clean_title = _clean_text(title)
    description_sentence = re.split(r"[.!?\n]", _clean_text(description))[0]
    sources = [("title_segment", part) for part in re.split(r"\||:|-", clean_title)]
    sources += [("full_title", clean_title), ("description", description_sentence)]
    ranked = []
    seen = set()
    for source, text in sources:
        words = _clean_query(text).split()
        removed = [word for word in words if word.lower() in WEAK_ANCHOR_WORDS]
        retained = [
            word for word in words
            if word.lower() not in WEAK_ANCHOR_WORDS and word.lower() not in STOP_WORDS
        ]
        # Keep a compact multiword phrase: enough context for subject/action, not packaging.
        retained = retained[:8]
        if len(retained) < 2:
            continue
        query = " ".join(retained)
        normalized = query.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        rationale = (
            "Retains the source's central multiword subject/action phrase"
            + (" while removing weak packaging terms." if removed else ".")
        )
        item = _hypothesis(query, source, removed, rationale)
        item["specificity"] = round(min(1.0, 0.18 * len(set(retained))), 3)
        ranked.append(item)
    ranked.sort(key=lambda item: (item["source"] == "description", -item["specificity"], len(item["query"])))
    return ranked[:limit]
