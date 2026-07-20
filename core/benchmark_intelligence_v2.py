"""Deterministic, explainable benchmark-neighborhood intelligence."""

import math
import re
from collections import Counter
from difflib import SequenceMatcher
from statistics import median


GENERIC = {"video", "official", "full", "hd", "viral", "clip", "new", "best"}
MISMATCH = {"compilation", "reaction", "reacts", "review", "breakdown", "reupload"}


def normalize(text):
    return " ".join(re.sub(r"[^\w\s]", " ", str(text or "").lower()).split())


def _tokens(text):
    return set(normalize(text).split())


def _seconds(value):
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", str(value or ""))
    if not match:
        return 0.0
    h, m, s = (int(part or 0) for part in match.groups())
    return h * 3600 + m * 60 + s


def score_candidate(video, target, hypotheses):
    title = normalize(video.get("title"))
    description = normalize(video.get("description"))
    target_title = normalize(target.get("title"))
    target_tokens = _tokens(target_title)
    title_tokens = _tokens(title)
    meaningful = {word for word in target_tokens if len(word) > 2 and word not in GENERIC}
    overlap = meaningful & title_tokens
    token_score = len(overlap) / max(len(meaningful), 1)
    phrases = [normalize(item.get("query", "") if isinstance(item, dict) else item) for item in hypotheses]
    phrase_matches = [phrase for phrase in phrases if phrase and phrase in title]
    phrase_score = max((len(_tokens(p)) / max(len(meaningful), 1) for p in phrase_matches), default=0.0)
    frequencies = Counter(word for phrase in phrases for word in _tokens(phrase))
    rare = {word for word in meaningful if frequencies.get(word, 0) <= 1}
    rare_score = len(rare & title_tokens) / max(len(rare), 1)
    matched = list(dict.fromkeys(video.get("matched_queries") or [video.get("matched_query", "")]))
    specificity_by_query = {
        normalize(item.get("query", "")): float(item.get("specificity", 0.5))
        for item in hypotheses if isinstance(item, dict)
    }
    query_specificity = max((specificity_by_query.get(normalize(q), 0.4) for q in matched), default=0.0)
    target_format = MISMATCH & target_tokens
    candidate_format = MISMATCH & title_tokens
    format_agreement = 1.0 if candidate_format == target_format else (0.5 if not candidate_format else 0.0)
    td, cd = _seconds(target.get("duration")), _seconds(video.get("duration"))
    duration = min(td, cd) / max(td, cd) if td and cd else 0.5
    reasons = []
    if overlap:
        reasons.append("Shared subject/action terms: " + ", ".join(sorted(overlap)))
    if phrase_matches:
        reasons.append("Meaningful query phrase appears in title")
    if query_specificity >= 0.7:
        reasons.append("Matched a specific query hypothesis")
    penalties = []
    penalty = 0.0
    mismatch = candidate_format - target_format
    if mismatch:
        penalty += 22.0
        penalties.append("Potential format mismatch: " + ", ".join(sorted(mismatch)))
    generic_ratio = len(title_tokens & GENERIC) / max(len(title_tokens), 1)
    if generic_ratio >= 0.4 or len(title_tokens) < 2:
        penalty += 12.0
        penalties.append("Title is too generic")
    missing = sum(not video.get(field) for field in ("title", "channel_title", "views"))
    if missing:
        penalty += 4.0 * missing
        penalties.append("Missing benchmark metadata")
    score = 100 * (0.34 * token_score + 0.22 * phrase_score + 0.16 * rare_score + 0.12 * query_specificity + 0.08 * format_agreement + 0.08 * duration) - penalty
    score = round(max(0.0, min(100.0, score)), 2)
    tier = "strong" if score >= 65 else "usable" if score >= 48 else "weak" if score >= 32 else "irrelevant"
    result = dict(video)
    result.update({
        "benchmark_relevance_score": score,
        "benchmark_relevance_tier": tier,
        "benchmark_relevance_reasons": reasons,
        "benchmark_relevance_penalties": penalties,
        "matched_queries": [q for q in matched if q],
    })
    return result


def deduplicate(candidates):
    kept = []
    removed = []
    for candidate in sorted(candidates, key=lambda item: (item.get("benchmark_relevance_score", 0), item.get("views", 0)), reverse=True):
        title = normalize(candidate.get("title"))
        duplicate = None
        for existing in kept:
            same_id = candidate.get("video_id") and candidate.get("video_id") == existing.get("video_id")
            similarity = SequenceMatcher(None, title, normalize(existing.get("title"))).ratio() if title else 0
            same_words = _tokens(title) == _tokens(existing.get("title"))
            same_channel_reupload = similarity >= 0.94 and same_words and normalize(candidate.get("channel_title")) == normalize(existing.get("channel_title"))
            if same_id or title == normalize(existing.get("title")) or same_channel_reupload:
                duplicate = existing
                break
        if duplicate:
            merged = list(dict.fromkeys(duplicate.get("matched_queries", []) + candidate.get("matched_queries", [])))
            duplicate["matched_queries"] = merged
            removed.append({"video_id": candidate.get("video_id", ""), "reason": "duplicate_or_near_duplicate"})
        else:
            kept.append(candidate)
    return kept, removed


def qualify_neighborhood(videos, target, hypotheses, minimum=8):
    scored = [score_candidate(video, target, hypotheses) for video in videos or []]
    deduped, duplicates = deduplicate(scored)
    thresholds = (65.0, 58.0, 52.0, 48.0)
    threshold = thresholds[0]
    qualified = []
    reason = "Strong relevance threshold retained enough candidates."
    for candidate_threshold in thresholds:
        pool = [item for item in deduped if item["benchmark_relevance_score"] >= candidate_threshold]
        threshold, qualified = candidate_threshold, pool
        if len(pool) >= minimum:
            if candidate_threshold < thresholds[0]:
                reason = f"Threshold relaxed modestly to {candidate_threshold:.0f} because the stronger threshold produced fewer than {minimum} candidates."
            break
    if threshold < thresholds[0] and len(qualified) < minimum:
        reason = f"Threshold relaxed modestly to the safe floor of {threshold:.0f}; the neighborhood remains smaller than {minimum}."
    rejected = [item for item in deduped if item not in qualified]
    rejection_reasons = Counter(
        "below_relevance_threshold" if item["benchmark_relevance_score"] < threshold else "not_selected"
        for item in rejected
    )
    warnings = []
    channels = {normalize(item.get("channel_title")) for item in qualified if item.get("channel_title")}
    query_coverage = {q for item in qualified for q in item.get("matched_queries", [])}
    if len(qualified) < 6:
        warnings.append("Qualified benchmark neighborhood is small.")
    if len(channels) < 3:
        warnings.append("Channel diversity is limited.")
    return qualified, {
        "raw_candidate_count": len(videos or []), "deduplicated_count": len(deduped),
        "qualified_candidate_count": len(qualified), "rejected_candidate_count": len(rejected) + len(duplicates),
        "rejection_reasons": dict(rejection_reasons), "duplicate_rejections": duplicates,
        "relevance_threshold_used": threshold, "relevance_threshold_reason": reason,
        "query_coverage": sorted(query_coverage), "channel_coverage": len(channels),
        "benchmark_quality_warnings": warnings,
    }


def _diverse_select(pool, size, reverse=False):
    selected, per_channel = [], Counter()
    ordered = sorted(pool, key=lambda item: (math.log1p(max(item.get("views", 0), 0)), item.get("benchmark_relevance_score", 0)), reverse=reverse)
    for cap in (1, 2):
        for item in ordered:
            channel = normalize(item.get("channel_title")) or item.get("video_id")
            if item in selected or per_channel[channel] >= cap:
                continue
            selected.append(item); per_channel[channel] += 1
            if len(selected) >= size:
                return selected
    # Diversity is a preference, not a validity gate when no alternatives remain.
    for item in ordered:
        if item not in selected:
            selected.append(item)
            if len(selected) >= size:
                return selected
    return selected


def select_performance_cohorts(candidates, preferred=5):
    credible = [item for item in candidates if max(int(item.get("views") or 0), 0) > 0]
    if len(credible) < 6:
        return [], [], {"selection_method": "insufficient_qualified_candidates", "fallback_reason": "At least six credible candidates are required."}
    logs = sorted(math.log1p(item["views"]) for item in credible)
    floor = math.exp(logs[max(0, int(len(logs) * 0.15) - 1)]) - 1
    non_junk = [item for item in credible if item["views"] >= max(10, floor)]
    size = min(preferred, len(non_junk) // 2)
    if size < 3:
        return [], [], {"selection_method": "insufficient_non_junk_candidates", "fallback_reason": "Near-zero candidates were excluded and fewer than three per group remained."}
    top = _diverse_select(non_junk, size, reverse=True)
    top_ids = {item.get("video_id") for item in top}
    top_median = median(item["views"] for item in top)
    lower_pool = [item for item in non_junk if item.get("video_id") not in top_ids and item["views"] <= top_median / 2]
    lower = _diverse_select(lower_pool, size, reverse=True)
    if len(lower) < 3:
        return [], [], {"selection_method": "log_view_diversity", "fallback_reason": "No credible lower cohort had a meaningful performance gap."}
    lower_median = median(item["views"] for item in lower)
    ratio = top_median / max(lower_median, 1)
    gap = math.log10(max(top_median, 1)) - math.log10(max(lower_median, 1))
    return top, lower, {
        "selection_method": "log_view_gap_with_channel_diversity", "performance_separation": round(gap, 3),
        "top_median_views": top_median, "lower_median_views": lower_median, "median_view_ratio": round(ratio, 3),
        "top_channel_count": len({normalize(x.get("channel_title")) for x in top}),
        "lower_channel_count": len({normalize(x.get("channel_title")) for x in lower}), "fallback_reason": "",
    }


def assess_benchmark_quality(qualified, top, lower, diagnostics, observation_ratio=0.0):
    relevance = sum(item.get("benchmark_relevance_score", 0) for item in qualified) / max(len(qualified), 1)
    group_size = min(1.0, min(len(top), len(lower)) / 4.0) if top and lower else 0.0
    channel = min(1.0, diagnostics.get("channel_coverage", 0) / 4.0)
    queries = min(1.0, len(diagnostics.get("query_coverage", [])) / 3.0)
    separation = min(1.0, diagnostics.get("median_view_ratio", 0) / 4.0)
    metadata = sum(all(item.get(k) not in (None, "") for k in ("title", "views", "channel_title")) for item in qualified) / max(len(qualified), 1)
    format_consistency = sum(
        not any("format mismatch" in penalty.lower() for penalty in item.get("benchmark_relevance_penalties", []))
        for item in qualified
    ) / max(len(qualified), 1)
    components = {"candidate_relevance": relevance / 100, "group_size": group_size, "channel_diversity": channel, "query_coverage": queries, "format_consistency": format_consistency, "performance_separation": separation, "metadata_completeness": metadata, "observation_availability": observation_ratio}
    weights = {"candidate_relevance": .24, "group_size": .15, "channel_diversity": .12, "query_coverage": .09, "format_consistency": .10, "performance_separation": .15, "metadata_completeness": .07, "observation_availability": .08}
    score = round(100 * sum(components[k] * weights[k] for k in weights), 1)
    eligible = score >= 65 and len(top) >= 3 and len(lower) >= 3 and diagnostics.get("median_view_ratio", 0) >= 1.8
    failures = []
    if not top or not lower: failures.append("coherent_performance_groups_unavailable")
    if score < 65: failures.append("quality_score_below_learning_floor")
    return {"score": score, "confidence": "high" if score >= 80 else "moderate" if score >= 65 else "limited", "components": {k: round(v, 3) for k, v in components.items()}, "warnings": diagnostics.get("benchmark_quality_warnings", []), "failure_reasons": failures, "eligible_for_directional_learning": eligible}
