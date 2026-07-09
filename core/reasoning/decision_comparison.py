from collections import Counter
from typing import Any, Dict, List, Set


def compare_creator_decisions(
    user_decisions: Dict[str, Any],
    benchmark_decisions: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compares user creator decisions against top and lower benchmark decisions.

    This module does not recommend.
    This module does not score.
    It only identifies decision-level differences.
    """

    user_types = _decision_types(user_decisions.get("decisions", []))

    top_counts = _group_decision_counts(
        benchmark_decisions.get("top_performers", [])
    )
    lower_counts = _group_decision_counts(
        benchmark_decisions.get("lower_performers", [])
    )

    top_types = set(top_counts.keys())
    lower_types = set(lower_counts.keys())

    matching_top = sorted(user_types.intersection(top_types))
    matching_lower = sorted(user_types.intersection(lower_types))

    missing_top = sorted(top_types.difference(user_types))
    unique_user = sorted(user_types.difference(top_types.union(lower_types)))

    stronger_only = sorted(top_types.difference(lower_types))
    weaker_only = sorted(lower_types.difference(top_types))

    return {
        "status": "success" if top_types or lower_types else "limited",
        "matching_top_decisions": matching_top,
        "matching_lower_decisions": matching_lower,
        "missing_top_decisions": missing_top,
        "unique_user_decisions": unique_user,
        "stronger_only_decisions": stronger_only,
        "weaker_only_decisions": weaker_only,
        "top_decision_counts": dict(top_counts),
        "lower_decision_counts": dict(lower_counts),
        "comparison_confidence": _confidence(
            top_counts=top_counts,
            lower_counts=lower_counts,
        ),
        "summary": _summary(
            matching_top=matching_top,
            matching_lower=matching_lower,
            missing_top=missing_top,
            stronger_only=stronger_only,
            weaker_only=weaker_only,
        ),
    }


def _decision_types(decisions: List[Dict[str, Any]]) -> Set[str]:
    return {
        decision.get("decision_type")
        for decision in decisions or []
        if decision.get("decision_type")
    }


def _group_decision_counts(group_items: List[Dict[str, Any]]) -> Counter:
    counter = Counter()

    for item in group_items or []:
        for decision in item.get("decisions", []):
            decision_type = decision.get("decision_type")
            if decision_type:
                counter[decision_type] += 1

    return counter


def _confidence(top_counts: Counter, lower_counts: Counter) -> str:
    top_total = sum(top_counts.values())
    lower_total = sum(lower_counts.values())

    if top_total >= 5 and lower_total >= 5:
        return "moderate"

    if top_total >= 2 and lower_total >= 2:
        return "limited"

    return "low"


def _summary(
    matching_top: List[str],
    matching_lower: List[str],
    missing_top: List[str],
    stronger_only: List[str],
    weaker_only: List[str],
) -> str:
    return (
        f"Decision comparison found {len(matching_top)} user decision(s) also seen "
        f"in stronger benchmarks, {len(matching_lower)} also seen in lower benchmarks, "
        f"{len(missing_top)} stronger benchmark decision(s) missing from the user intro, "
        f"{len(stronger_only)} decision(s) more associated with stronger benchmarks, "
        f"and {len(weaker_only)} decision(s) more associated with lower benchmarks."
    )