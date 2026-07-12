"""
Stratify Content Understanding

AI understands what the video is about and generates benchmark queries.

No hardcoded niches.
No category tables.
No keyword rule lists.

AI understands.
Code validates, cleans, and falls back safely.
"""

import json
import re

from core.providers.provider_router import observe_text


def _clean_text(value):
    value = str(value or "").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def _extract_json(text):
    text = str(text or "").strip()

    text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^```", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return {}

    try:
        return json.loads(text[start : end + 1])
    except Exception:
        return {}


def _dedupe_queries(queries):
    cleaned = []
    seen = set()

    for query in queries or []:
        query = _clean_text(query)

        if not query:
            continue

        key = query.lower()

        if key in seen:
            continue

        seen.add(key)
        cleaned.append(query)

    return cleaned[:5]


def _fallback_queries(video):
    title = _clean_text((video or {}).get("title", ""))

    if not title:
        return ["creator video benchmark"]

    parts = re.split(r"\||-|–|—|:", title)
    parts = [_clean_text(part) for part in parts if _clean_text(part)]

    if parts:
        return [parts[0], title][:5]

    return [title]


def _build_prompt(video, intro_observation=None):
    video = video or {}
    intro_observation = intro_observation or {}

    title = _clean_text(video.get("title", ""))
    description = _clean_text(video.get("description", ""))
    channel_title = _clean_text(video.get("channel_title", ""))

    return f"""
You are Stratify's Content Understanding Engine.

Your job:
Understand what this YouTube video is actually about and generate useful benchmark search queries.

Important:
- Do NOT recommend improvements.
- Do NOT predict views, retention, virality, or performance.
- Do NOT simply copy the full title if it is a quote, clickbait phrase, or overly specific sentence.
- Generate search queries that would find similar successful videos.
- If the content source/topic is uncertain, be honest and use cautious queries.
- Treat observed intro evidence as stronger than shared names in metadata.
- Distinguish experiencing the depicted material from hearing someone discuss,
  evaluate, summarize, teach, or report on that material. Describe the actual
  relationship in free-form language; do not choose from a label list.
- A shared person, title, object, event, or topic does not establish the same
  viewer intent or storytelling job.
- Return ONLY valid JSON.

Video metadata:
Title: {title}
Channel: {channel_title}
Description: {description[:900]}

Intro observation:
{json.dumps(intro_observation, ensure_ascii=False)[:900]}

Return this JSON shape:

{{
  "subject": "",
  "viewer_intent": "",
  "presentation_style": "",
  "storytelling_format": "",
  "source_context": "",
  "benchmark_search_queries": [],
  "confidence": "low",
  "reason": ""
}}

Rules:
- Use short, free-form descriptions grounded in the supplied evidence.
- subject: what is actually being shown or discussed.
- viewer_intent: the experience or outcome a viewer came for, including whether
  the viewer consumes the depicted events directly or consumes interpretation.
- presentation_style: how the material is visibly or verbally presented.
- storytelling_format: how the opening delivers or structures its promise.
- source_context: the relationship between the uploader/presenter and the material, when evidence supports it.
- Do not choose from a predefined taxonomy and do not infer missing evidence.
- benchmark_search_queries: 3 to 5 useful YouTube search queries.
- confidence: high, moderate, or low.
"""


def understand_content(video, intro_observation=None, timeout_seconds=30):
    provider_result = observe_text(
        prompt=_build_prompt(video, intro_observation),
        timeout_seconds=timeout_seconds,
    )

    parsed = {}

    if provider_result.get("status") == "success":
        parsed = _extract_json(provider_result.get("content", ""))

    queries = _dedupe_queries(parsed.get("benchmark_search_queries", []))

    if not queries:
        queries = _fallback_queries(video)

    subject = _clean_text(parsed.get("subject") or parsed.get("primary_subject")) or "Unknown"
    viewer_intent = _clean_text(parsed.get("viewer_intent") or parsed.get("audience_intent")) or "Unknown"
    presentation_style = _clean_text(parsed.get("presentation_style")) or "Unknown"
    storytelling_format = _clean_text(parsed.get("storytelling_format") or parsed.get("format")) or "Unknown"
    source_context = _clean_text(parsed.get("source_context") or parsed.get("topic_or_source")) or "Unknown"

    return {
        "category": presentation_style,
        "subcategory": storytelling_format,
        "micro_niche": subject,
        "search_query": queries[0],
        "search_queries": queries,
        "candidate_queries": queries,
        "confidence": _clean_text(parsed.get("confidence", "")) or "low",
        "reason": _clean_text(parsed.get("reason", "")) or (
            "Generated benchmark queries from AI content understanding."
        ),
        "content_understanding": {
            "subject": subject,
            "viewer_intent": viewer_intent,
            "presentation_style": presentation_style,
            "storytelling_format": storytelling_format,
            "source_context": source_context,
            # Compatibility aliases for existing report surfaces.
            "content_type": presentation_style,
            "topic_or_source": source_context,
            "primary_subject": subject,
            "format": storytelling_format,
            "audience_intent": viewer_intent,
            "benchmark_search_queries": queries,
            "provider": provider_result.get("provider", ""),
            "warnings": provider_result.get("warnings", []),
        },
    }


def understand_category(video):
    """
    Backward-compatible wrapper for older pipeline calls.
    """
    return understand_content(video, intro_observation=None)
