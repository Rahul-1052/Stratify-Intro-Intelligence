from collections import Counter
from typing import Any, Dict, List


def learn_benchmark_patterns(
    benchmark_features: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Learns recurring observable creative patterns across
    successful and lower-performing benchmark intros.

    This module never recommends.
    It never scores.
    It only summarizes repeated evidence.
    """

    top_patterns = _learn_group_patterns(
        benchmark_features.get("top_performers", [])
    )

    lower_patterns = _learn_group_patterns(
        benchmark_features.get("lower_performers", [])
    )

    discriminative_patterns = _find_discriminative_patterns(
        top_patterns,
        lower_patterns,
    )

    return {
        "status": "success",
        "top_patterns": top_patterns,
        "lower_patterns": lower_patterns,
        "discriminative_patterns": discriminative_patterns,
        "summary": (
            f"Learned {len(discriminative_patterns)} recurring "
            "benchmark patterns."
        ),
    }


def _learn_group_patterns(items):

    counters = {}

    sample_count = 0

    for item in items:

        if item.get("status") != "success":
            continue

        sample_count += 1

        feature_summary = (
            item.get("features", {})
            .get("feature_summary", {})
        )

        for feature, value in feature_summary.items():

            if feature not in counters:
                counters[feature] = Counter()

            counters[feature][str(value)] += 1

    learned = {}

    for feature, counter in counters.items():

        if not counter:
            continue

        value, count = counter.most_common(1)[0]

        learned[feature] = {
            "dominant_value": value,
            "count": count,
            "sample_count": sample_count,
            "frequency": (
                round(count / sample_count, 2)
                if sample_count
                else 0.0
            ),
        }

    return learned


def _find_discriminative_patterns(
    top_patterns,
    lower_patterns,
):

    results = []

    for feature, top in top_patterns.items():

        lower = lower_patterns.get(feature)

        if not lower:
            continue

        if top["dominant_value"] == lower["dominant_value"]:
            continue

        results.append(
            {
                "feature": feature,
                "top_pattern": top,
                "lower_pattern": lower,
                "frequency_gap": round(
                    top["frequency"] - lower["frequency"],
                    2,
                ),
            }
        )

    results.sort(
        key=lambda item: abs(item["frequency_gap"]),
        reverse=True,
    )

    return results