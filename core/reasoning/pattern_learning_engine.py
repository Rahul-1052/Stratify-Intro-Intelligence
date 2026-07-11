from collections import Counter
from typing import Any, Dict, List

from core.pattern_discovery import _extract_summary, _normalize_value


def learn_benchmark_patterns(
    benchmark_features: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Summarize repeated observable evidence without recommending or scoring."""
    top_patterns = _learn_group_patterns(benchmark_features.get("top_performers", []))
    lower_patterns = _learn_group_patterns(benchmark_features.get("lower_performers", []))
    discriminative_patterns = _find_discriminative_patterns(top_patterns, lower_patterns)

    return {
        "status": "success" if top_patterns or lower_patterns else "limited",
        "top_patterns": top_patterns,
        "lower_patterns": lower_patterns,
        "discriminative_patterns": discriminative_patterns,
        "summary": f"Learned {len(discriminative_patterns)} recurring benchmark patterns.",
    }


def _learn_group_patterns(items):
    counters = {}
    sample_count = 0

    for item in items or []:
        feature_summary = _extract_summary(item)
        if not feature_summary:
            continue

        sample_count += 1
        for feature, raw_value in feature_summary.items():
            value = _normalize_value(raw_value)
            if value is None:
                continue
            counters.setdefault(feature, Counter())[value] += 1

    learned = {}
    for feature, counter in counters.items():
        if not counter:
            continue
        value, count = counter.most_common(1)[0]
        learned[feature] = {
            "dominant_value": value,
            "count": count,
            "sample_count": sample_count,
            "frequency": round(count / sample_count, 2) if sample_count else 0.0,
            "distribution": dict(counter),
        }

    return learned


def _find_discriminative_patterns(top_patterns, lower_patterns):
    results = []
    for feature, top in top_patterns.items():
        lower = lower_patterns.get(feature)
        if not lower or top["dominant_value"] == lower["dominant_value"]:
            continue

        # One-off values are observations, not learned recurring patterns.
        if top["count"] <= 1 or lower["count"] <= 1:
            continue

        lower_share_for_top = lower["distribution"].get(
            top["dominant_value"], 0
        ) / max(lower["sample_count"], 1)

        results.append(
            {
                "feature": feature,
                "top_pattern": top,
                "lower_pattern": lower,
                # Contrast the same value across groups. Subtracting the
                # prevalence of two different modes is not meaningful.
                "frequency_gap": round(top["frequency"] - lower_share_for_top, 2),
            }
        )

    results.sort(key=lambda item: abs(item["frequency_gap"]), reverse=True)
    return results
