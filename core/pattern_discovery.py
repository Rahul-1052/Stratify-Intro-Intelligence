from collections import Counter


DESCRIPTIVE_FEATURES = {
    "dominant_lighting",
    "dominant_color_feel",
}

ACTIONABLE_FEATURES = {
    "human_presence",
    "text_overlay",
    "scene_type",
    "visual_energy",
    "motion_level",
    "scene_change_count",
    "scene_changes",
    "pacing_level",
}

FEATURE_MAP = {
    "dominant_lighting": "lighting",
    "dominant_color_feel": "color feel",
    "human_presence": "human presence",
    "text_overlay": "text overlay",
    "scene_type": "scene type",
    "visual_energy": "visual energy",
    "motion_level": "motion level",
    "scene_change_count": "scene changes",
    "pacing_level": "pacing level",
}


def _get_summary(item):
    if not isinstance(item, dict):
        return {}

    if "feature_summary" in item:
        return item.get("feature_summary", {}) or {}

    if "features" in item:
        return item.get("features", {}).get("feature_summary", {}) or {}

    return {}


def _normalize(value):
    if value is None:
        return "unknown"

    if isinstance(value, str):
        value = value.strip().lower()
        return value if value else "unknown"

    return value


def _collect_values(items, feature):
    values = []

    for item in items or []:
        if item.get("status") == "failed":
            continue

        summary = _get_summary(item)
        value = _normalize(summary.get(feature, "unknown"))

        if value != "unknown":
            values.append(value)

    return values


def _dominant(values):
    if not values:
        return {
            "value": "unknown",
            "count": 0,
            "total": 0,
            "is_dominant": False,
        }

    counts = Counter(values)
    value, count = counts.most_common(1)[0]

    tied = len(counts.most_common()) > 1 and counts.most_common()[1][1] == count

    return {
        "value": value,
        "count": count,
        "total": len(values),
        "is_dominant": count >= 2 and not tied,
    }


def _evidence_text(group_name, dominant):
    if dominant["total"] == 0:
        return f"{group_name}: no classified benchmark intros available."

    if not dominant["is_dominant"]:
        return (
            f"{group_name}: no clear dominant value across "
            f"{dominant['total']} classified intro(s)."
        )

    return (
        f"{group_name}: '{dominant['value']}' appeared in "
        f"{dominant['count']} of {dominant['total']} classified intro(s)."
    )


def _status(feature, user_value, top_dom, lower_dom):
    if user_value == "unknown":
        return "insufficient_evidence"

    if feature in DESCRIPTIVE_FEATURES:
        if top_dom["is_dominant"] and user_value == top_dom["value"]:
            return "observed_alignment"
        if top_dom["is_dominant"] and user_value != top_dom["value"]:
            return "observed_difference"
        return "insufficient_evidence"

    if feature not in ACTIONABLE_FEATURES:
        return "insufficient_evidence"

    if not top_dom["is_dominant"]:
        return "insufficient_evidence"

    if not lower_dom["is_dominant"]:
        return "insufficient_evidence"

    if top_dom["value"] == lower_dom["value"]:
        return "non_discriminative"

    if user_value == top_dom["value"]:
        return "aligned_with_top"

    if user_value == lower_dom["value"]:
        return "risk_signal"

    return "missing_winning_feature"


def _explanation(label, feature, user_value, top_dom, lower_dom, status):
    if user_value == "unknown":
        return f"{label}: the user value is unknown, so no position is assigned."

    if status == "observed_alignment":
        return (
            f"{label}: the observed user value '{user_value}' matches the dominant "
            "top benchmark value. This observation does not affect the verdict."
        )

    if status == "observed_difference":
        return (
            f"{label}: the observed user value '{user_value}' differs from the "
            f"dominant top benchmark value '{top_dom['value']}'. This observation "
            "does not affect signals, the verdict, or recommendations."
        )

    if not top_dom["is_dominant"]:
        return f"{label}: top performers did not show a clear dominant value."

    if feature in ACTIONABLE_FEATURES and not lower_dom["is_dominant"]:
        return (
            f"{label}: lower performers did not show a clear dominant value, "
            "so this feature cannot position the user."
        )

    if status == "non_discriminative":
        return (
            f"{label}: '{top_dom['value']}' dominates both benchmark groups, "
            "so this feature does not distinguish them."
        )

    if status == "aligned_with_top":
        return (
            f"{label}: user value '{user_value}' matches the dominant top benchmark "
            f"value and differs from the lower benchmark value '{lower_dom['value']}'."
        )

    if status == "risk_signal":
        return (
            f"{label}: user value '{user_value}' matches the dominant lower benchmark "
            f"value and differs from the top benchmark value '{top_dom['value']}'."
        )

    if status == "missing_winning_feature":
        return (
            f"{label}: user value '{user_value}' differs from the dominant top "
            f"benchmark value '{top_dom['value']}'."
        )

    return f"{label}: evidence is insufficient for a reliable position."


def _recommendation_for(item):
    label = item["label"]
    top_value = item["top_dominant_value"]
    lower_value = item["lower_dominant_value"]
    user_value = item["user_value"]

    return {
        "title": f"Experiment with {label}",
        "evidence": (
            f"Top benchmark intros most often showed '{top_value}', while lower "
            f"benchmark intros most often showed '{lower_value}'. Your intro showed "
            f"'{user_value}'."
        ),
        "why_it_matters": (
            "This is an observed difference between benchmark groups. It does not "
            "establish cause, but it is worth testing."
        ),
        "suggested_test": f"Test an opening segment closer to the top benchmark pattern for {label}.",
        "confidence": "limited",
    }


def _confidence(top_features, lower_features, comparisons):
    top_count = len([x for x in top_features or [] if x.get("status") != "failed"])
    lower_count = len([x for x in lower_features or [] if x.get("status") != "failed"])

    usable = [
        item for item in comparisons
        if item["status"] in {
            "aligned_with_top",
            "risk_signal",
            "missing_winning_feature",
        }
    ]

    if top_count >= 3 and lower_count >= 3 and len(usable) >= 2:
        return {
            "level": "moderate",
            "reason": "Enough benchmark intros and multiple actionable comparisons were available.",
        }

    if top_count >= 2 and lower_count >= 2 and len(usable) >= 1:
        return {
            "level": "limited",
            "reason": "Some benchmark evidence was available, but the comparison set is still small.",
        }

    return {
        "level": "low",
        "reason": "Too few benchmark intros or contrasting actionable feature values were available.",
    }


def _final_verdict(comparisons, confidence_level):
    if confidence_level == "low":
        return "The available benchmark evidence is too limited for a clear position."

    aligned = [x for x in comparisons if x["status"] == "aligned_with_top"]
    missing = [x for x in comparisons if x["status"] == "missing_winning_feature"]
    risks = [x for x in comparisons if x["status"] == "risk_signal"]

    if risks:
        return (
            f"Your intro matches {len(risks)} lower-benchmark pattern(s), "
            f"misses {len(missing)} top-benchmark pattern(s), and aligns with "
            f"{len(aligned)} top-benchmark pattern(s)."
        )

    if missing:
        return (
            f"Your intro misses {len(missing)} top-benchmark pattern(s) and aligns "
            f"with {len(aligned)} top-benchmark pattern(s)."
        )

    if aligned:
        return (
            "Your intro aligns with the strongest actionable benchmark patterns "
            "Stratify could reliably compare."
        )

    return "No clear actionable difference was found from the current benchmark evidence."


def discover_patterns(top_features, lower_features, user_features):
    user_summary = _get_summary(user_features)

    feature_comparison = []
    missing_winning_features = []
    risk_signals = []
    recommendations = []
    user_position = []

    for feature, label in FEATURE_MAP.items():
        user_value = _normalize(user_summary.get(feature, "unknown"))

        if feature == "scene_change_count" and user_value == "unknown":
            user_value = _normalize(user_summary.get("scene_changes", "unknown"))

        top_values = _collect_values(top_features, feature)
        lower_values = _collect_values(lower_features, feature)

        top_dom = _dominant(top_values)
        lower_dom = _dominant(lower_values)

        status = _status(feature, user_value, top_dom, lower_dom)
        explanation = _explanation(label, feature, user_value, top_dom, lower_dom, status)

        item = {
            "feature": feature,
            "label": label,
            "user_value": user_value,
            "top_dominant_value": top_dom["value"],
            "top_evidence_count": top_dom["count"],
            "top_evidence_total": top_dom["total"],
            "top_evidence": _evidence_text("Top benchmarks", top_dom),
            "lower_dominant_value": lower_dom["value"],
            "lower_evidence_count": lower_dom["count"],
            "lower_evidence_total": lower_dom["total"],
            "lower_evidence": _evidence_text("Lower benchmarks", lower_dom),
            "status": status,
            "explanation": explanation,
        }

        feature_comparison.append(item)

        if status in {"aligned_with_top", "risk_signal", "missing_winning_feature"}:
            user_position.append(explanation)

        if status == "missing_winning_feature":
            missing_winning_features.append(item)
            recommendations.append(_recommendation_for(item))

        if status == "risk_signal":
            risk_signals.append(item)
            recommendations.append(_recommendation_for(item))

    confidence = _confidence(top_features, lower_features, feature_comparison)

    return {
        "feature_comparison": feature_comparison,
        "user_position": user_position,
        "missing_winning_features": missing_winning_features,
        "risk_signals": risk_signals,
        "recommendations": recommendations,
        "final_verdict": _final_verdict(feature_comparison, confidence["level"]),
        "confidence": confidence["level"],
        "confidence_reason": confidence["reason"],
    }