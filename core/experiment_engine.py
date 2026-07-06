"""
Stratify Experiment Engine

Turns benchmark contrast evidence into multiple creator experiments.

Rules:
- No motivational fluff.
- No hallucinated certainty.
- No performance prediction.
- Every experiment must trace back to user/top/lower evidence.
"""

ACTIONABLE_STATUS_HINTS = {
    "worth_testing",
    "missing_winning_feature",
    "matches_lower",
    "risk_signal",
}


def _safe_text(value, fallback="unknown"):
    value = str(value or "").strip()
    return value if value else fallback


def _confidence_from_comparison(item):
    top_total = item.get("top_evidence_total", 0) or 0
    lower_total = item.get("lower_evidence_total", 0) or 0
    top_share = item.get("top_evidence_share", 0) or 0
    lower_share = item.get("lower_evidence_share", 0) or 0

    if top_total >= 3 and lower_total >= 3 and top_share >= 0.65 and lower_share >= 0.65:
        return "High"

    if top_total >= 2 and lower_total >= 2 and top_share >= 0.5:
        return "Medium"

    return "Low"


def _experiment_title(label, top_value, user_value):
    label = _safe_text(label, "this signal")
    top_value = _safe_text(top_value)
    user_value = _safe_text(user_value)

    if user_value == "unknown":
        return f"Clarify {label}"

    return f"Test {label}: move from '{user_value}' toward '{top_value}'"


def _experiment_action(label, top_value, user_value):
    label = _safe_text(label, "this signal")
    top_value = _safe_text(top_value)
    user_value = _safe_text(user_value)

    return (
        f"Create a version of the next upload where {label} is closer to "
        f"the stronger benchmark pattern: '{top_value}', instead of the current "
        f"observed pattern: '{user_value}'."
    )


def _is_useful_comparison(item):
    if not isinstance(item, dict):
        return False

    if not item.get("actionable", False):
        return False

    user_value = item.get("user_value")
    top_value = item.get("top_dominant_value")
    lower_value = item.get("lower_dominant_value")

    if not user_value or not top_value:
        return False

    if str(top_value).lower() == "unknown":
        return False

    if str(user_value).lower() == str(top_value).lower():
        return False

    status = str(item.get("status", "")).lower()

    if status in ACTIONABLE_STATUS_HINTS:
        return True

    if lower_value and str(lower_value).lower() != "unknown":
        return str(user_value).lower() == str(lower_value).lower()

    return item.get("top_evidence_count", 0) >= 2


def _rank_score(item):
    score = 0

    if item.get("actionable"):
        score += 2

    if item.get("top_dominant_value") and item.get("user_value"):
        if str(item["top_dominant_value"]).lower() != str(item["user_value"]).lower():
            score += 2

    if item.get("lower_dominant_value"):
        if str(item.get("lower_dominant_value")).lower() == str(item.get("user_value")).lower():
            score += 2

    score += float(item.get("top_evidence_share", 0) or 0)
    score += float(item.get("lower_evidence_share", 0) or 0)

    score += min(int(item.get("top_evidence_count", 0) or 0), 5) * 0.2
    score += min(int(item.get("lower_evidence_count", 0) or 0), 5) * 0.2

    return score


def generate_experiment_board(patterns, max_experiments=5):
    comparisons = patterns.get("feature_comparison", []) if isinstance(patterns, dict) else []

    useful = [
        item for item in comparisons
        if _is_useful_comparison(item)
    ]

    useful = sorted(useful, key=_rank_score, reverse=True)

    experiments = []

    for item in useful[:max_experiments]:
        label = _safe_text(item.get("label"), item.get("feature", "this signal"))
        user_value = _safe_text(item.get("user_value"))
        top_value = _safe_text(item.get("top_dominant_value"))
        lower_value = _safe_text(item.get("lower_dominant_value"))

        confidence = _confidence_from_comparison(item)

        experiments.append(
            {
                "title": _experiment_title(label, top_value, user_value),
                "experiment": _experiment_action(label, top_value, user_value),
                "confidence": confidence,
                "why": (
                    f"Top benchmark pattern: '{top_value}'. "
                    f"Lower benchmark pattern: '{lower_value}'. "
                    f"Your intro: '{user_value}'."
                ),
                "evidence": {
                    "feature": item.get("feature"),
                    "label": label,
                    "user_value": user_value,
                    "top_dominant_value": top_value,
                    "top_evidence": item.get("top_evidence", ""),
                    "lower_dominant_value": lower_value,
                    "lower_evidence": item.get("lower_evidence", ""),
                    "explanation": item.get("explanation", ""),
                },
            }
        )

    if not experiments:
        return {
            "status": "insufficient_evidence",
            "summary": "No evidence-backed experiments met the current threshold.",
            "experiments": [],
        }

    return {
        "status": "success",
        "summary": (
            f"Stratify found {len(experiments)} evidence-backed experiment(s) "
            "by contrasting stronger and weaker benchmark intros."
        ),
        "experiments": experiments,
    }