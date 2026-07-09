from typing import Any, Dict, List

from core.reasoning.creator_decision_engine import infer_creator_decisions


def infer_benchmark_decisions(
    benchmark_features: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Infers creator decisions for top and lower benchmark intros.

    Reuses the same decision logic used for the user's intro.
    No separate benchmark-only reasoning.
    """

    top_decisions = _infer_group_decisions(
        benchmark_features.get("top_performers", [])
    )

    lower_decisions = _infer_group_decisions(
        benchmark_features.get("lower_performers", [])
    )

    return {
        "status": "success" if top_decisions or lower_decisions else "limited",
        "top_performers": top_decisions,
        "lower_performers": lower_decisions,
        "summary": _summarize(top_decisions, lower_decisions),
    }


def _infer_group_decisions(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []

    for item in items or []:
        if item.get("status") != "success":
            continue

        understanding = item.get("understanding", {})

        decision_result = infer_creator_decisions(understanding)

        results.append({
            "video": item.get("video", {}),
            "decisions": decision_result.get("decisions", []),
            "decision_count": decision_result.get("decision_count", 0),
            "summary": decision_result.get("summary", ""),
        })

    return results


def _summarize(
    top_decisions: List[Dict[str, Any]],
    lower_decisions: List[Dict[str, Any]],
) -> str:
    return (
        f"Inferred decisions for {len(top_decisions)} top benchmark intro(s) "
        f"and {len(lower_decisions)} lower benchmark intro(s)."
    )