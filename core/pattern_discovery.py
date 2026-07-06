from collections import Counter


FEATURE_MAP = {
    "dominant_lighting": "lighting",
    "dominant_color_feel": "color feel",
    "human_presence": "human presence",
    "text_overlay": "text overlay",
    "scene_type": "scene type",
    "visual_energy": "visual energy",
    "motion_level": "motion level",
    "scene_changes": "scene changes",
    "scene_change_count": "scene changes",
    "pacing_level": "pacing level",
    "first_frame_strength": "first frame strength",
    "opening_action_type": "opening action type",
    "hook_visible_in_first_3_seconds": "hook visible in first 3 seconds",
    "subject_clarity": "subject clarity",
    "conflict_visible": "conflict visible",
    "payoff_teased": "payoff teased",
    "curiosity_gap": "curiosity gap",
}

VISUAL_FEATURES = {
    "dominant_lighting",
    "dominant_color_feel",
    "human_presence",
    "text_overlay",
    "scene_type",
    "visual_energy",
    "motion_level",
    "scene_changes",
    "scene_change_count",
    "pacing_level",
}

STORYTELLING_FEATURES = {
    "first_frame_strength",
    "opening_action_type",
    "hook_visible_in_first_3_seconds",
    "subject_clarity",
    "conflict_visible",
    "payoff_teased",
    "curiosity_gap",
}

ACTIONABLE_FEATURES = {
    "human_presence",
    "text_overlay",
    "scene_type",
    "visual_energy",
    "motion_level",
    "scene_changes",
    "scene_change_count",
    "pacing_level",
    "first_frame_strength",
    "opening_action_type",
    "hook_visible_in_first_3_seconds",
    "subject_clarity",
    "conflict_visible",
    "payoff_teased",
    "curiosity_gap",
}

OBSERVATION_ONLY_FEATURES = {
    "dominant_lighting",
    "dominant_color_feel",
}

UNKNOWN_VALUES = {None, "", "unknown", "unavailable", "not_detected"}
POSITIONED_STATUSES = {
    "aligned_with_top",
    "missing_winning_feature",
    "risk_signal",
}
STORYTELLING_TITLES = {
    "first_frame_strength": "Strengthen the opening frame",
    "hook_visible_in_first_3_seconds": "Make the hook visible sooner",
    "subject_clarity": "Make the main subject clear faster",
    "conflict_visible": "Show the tension earlier",
    "payoff_teased": "Tease the payoff earlier",
    "curiosity_gap": "Create a stronger reason to keep watching",
}


def _get_summary(feature):
    if not isinstance(feature, dict):
        return {}
    if "feature_summary" in feature:
        return feature.get("feature_summary", {}) or {}
    if "features" in feature:
        return feature.get("features", {}).get("feature_summary", {}) or {}
    return {}


def _normalize_value(value):
    if isinstance(value, str):
        value = value.strip().lower()
    if value in UNKNOWN_VALUES:
        return "unknown"
    return value


def _collect_values(features, key):
    values = []
    for item in features or []:
        value = _normalize_value(_get_summary(item).get(key))
        if value != "unknown":
            values.append(value)
    return values


def _dominant_value(values):
    if not values:
        return {
            "value": "unknown",
            "count": 0,
            "total": 0,
            "share": 0.0,
            "is_strong": False,
        }

    ranked = Counter(values).most_common()
    value, count = ranked[0]
    total = len(values)
    share = count / total
    tied = len(ranked) > 1 and ranked[1][1] == count
    return {
        "value": value,
        "count": count,
        "total": total,
        "share": round(share, 2),
        "is_strong": count >= 2 and share >= 0.6 and not tied,
    }


def _evidence_text(group_name, dominant):
    if dominant["total"] == 0:
        return f"{group_name}: no classified benchmark intros available."
    if not dominant["is_strong"]:
        return (
            f"{group_name}: no clear dominant value across "
            f"{dominant['total']} classified intro(s)."
        )
    return (
        f"{group_name}: '{dominant['value']}' appeared in "
        f"{dominant['count']} of {dominant['total']} classified intro(s)."
    )


def _comparison_status(key, user_value, top, lower):
    if user_value == "unknown" or not top["is_strong"]:
        return "insufficient_evidence"

    if key in OBSERVATION_ONLY_FEATURES:
        if user_value == top["value"]:
            return "observed_alignment"
        return "observed_difference"

    if not lower["is_strong"]:
        return "insufficient_evidence"
    if top["value"] == lower["value"]:
        return "non_discriminative"
    if user_value == top["value"]:
        return "aligned_with_top"
    if user_value == lower["value"]:
        return "risk_signal"
    return "missing_winning_feature"


def _comparison_explanation(label, user_value, top, lower, status):
    if user_value == "unknown":
        return f"{label}: the user value is unknown, so no position is assigned."
    if not top["is_strong"]:
        return f"{label}: top performers did not show a clear dominant value."
    if status == "observed_alignment":
        return (
            f"{label}: the observed user value '{user_value}' matches the dominant "
            "top benchmark value. This observation does not affect the verdict."
        )
    if status == "observed_difference":
        return (
            f"{label}: the observed user value '{user_value}' differs from the "
            f"dominant top benchmark value '{top['value']}'. This observation does "
            "not affect signals, the verdict, or recommendations."
        )
    if not lower["is_strong"]:
        return (
            f"{label}: lower performers did not show a clear dominant value, so "
            "this feature cannot position the user."
        )
    if status == "non_discriminative":
        return (
            f"{label}: '{top['value']}' dominates both benchmark groups, so this "
            "feature does not distinguish them."
        )
    if status == "aligned_with_top":
        return (
            f"{label}: the user value '{user_value}' matches the dominant top "
            f"benchmark value and differs from the lower value '{lower['value']}'."
        )
    if status == "risk_signal":
        return (
            f"{label}: the user value '{user_value}' matches the dominant lower "
            f"benchmark value and differs from the top value '{top['value']}'."
        )
    if status == "missing_winning_feature":
        return (
            f"{label}: the user value '{user_value}' differs from the dominant top "
            f"benchmark value '{top['value']}' and the lower value "
            f"'{lower['value']}'."
        )
    return f"{label}: current evidence is insufficient for positioning."


def _successful_benchmark_count(items):
    return sum(bool(_get_summary(item)) for item in items or [])


def _confidence(top_features, lower_features, comparisons):
    positioned = sum(
        item["status"] in POSITIONED_STATUSES
        for item in comparisons
        if item["actionable"]
    )
    top_count = _successful_benchmark_count(top_features)
    lower_count = _successful_benchmark_count(lower_features)

    if top_count >= 3 and lower_count >= 3 and positioned >= 2:
        return {
            "level": "moderate",
            "reason": (
                "Three top and three lower benchmark intros were analyzed, with "
                "at least two actionable features showing usable group contrast."
            ),
        }
    if top_count >= 2 and lower_count >= 2 and positioned >= 1:
        return {
            "level": "limited",
            "reason": (
                "Both benchmark groups supplied usable evidence, but the sample "
                "or number of contrasting actionable features remains small."
            ),
        }
    return {
        "level": "low",
        "reason": (
            "Too few benchmark intros or contrasting actionable feature values "
            "were available."
        ),
    }


def _recommendation_confidence(top, lower, overall_confidence):
    if (
        overall_confidence == "moderate"
        and top["total"] >= 3
        and lower["total"] >= 3
        and top["share"] >= 0.67
        and lower["share"] >= 0.67
    ):
        return "moderate"
    return "limited"


def _suggested_test(feature, top_value, user_value):
    if feature == "first_frame_strength":
        return (
            f"Test an opening frame with '{top_value}' strength against the current "
            f"observed value '{user_value}'."
        )
    if feature == "opening_action_type":
        return (
            f"Test opening with '{top_value}' as the first visible action instead "
            f"of the current observed action '{user_value}'."
        )
    if feature == "hook_visible_in_first_3_seconds":
        return (
            "Test making the core hook visible in the first 3 seconds and compare "
            f"it with the current observed value '{user_value}'."
        )
    if feature == "subject_clarity":
        return (
            f"Test making the main subject '{top_value}' earlier in the intro "
            f"against the current observed clarity '{user_value}'."
        )
    if feature == "conflict_visible":
        return (
            "Test showing the central tension earlier in the intro and compare it "
            f"with the current observed value '{user_value}'."
        )
    if feature == "payoff_teased":
        return (
            "Test teasing the expected payoff earlier while keeping the same topic "
            f"and compare it with the current observed value '{user_value}'."
        )
    if feature == "curiosity_gap":
        return (
            f"Test a stronger curiosity gap using the benchmark pattern '{top_value}' "
            f"against the current observed value '{user_value}'."
        )
    if feature == "motion_level":
        return (
            f"Test a {top_value}-motion opening by adjusting how much visible "
            "movement occurs during the first 15 seconds."
        )
    if feature == "scene_change_count":
        return (
            f"Test an opening with about {top_value} detected visual changes in "
            f"the first 15 seconds against the current observed count of {user_value}."
        )
    if feature == "pacing_level":
        return (
            f"Test a {top_value}-paced opening by adjusting how often the visual "
            "changes during the first 15 seconds."
        )
    if feature == "visual_energy":
        return (
            f"Test a {top_value}-energy opening by varying movement and edit "
            "frequency together while keeping the content consistent."
        )
    if feature == "human_presence":
        direction = "with" if top_value == "present" else "without"
        return (
            f"Test an opening {direction} a clearly visible person and compare it "
            "with the current version."
        )
    if feature == "text_overlay":
        direction = "with" if top_value == "present" else "without"
        return (
            f"Test an opening {direction} persistent on-screen text and compare it "
            "with the current version."
        )
    return (
        f"Test the observed scene format '{top_value}' against the current format "
        f"'{user_value}' while keeping other intro elements consistent."
    )


def _recommendation_title(feature, label):
    if feature in STORYTELLING_TITLES:
        return STORYTELLING_TITLES[feature]
    return f"Test the observed {label} pattern"


def _why_it_matters(feature):
    if feature in STORYTELLING_FEATURES:
        return (
            "This storytelling signal differed between the benchmark groups in the "
            "current sample. The comparison is evidence-based but correlational, "
            "so it should be tested rather than treated as a guaranteed cause."
        )
    return (
        "This observable feature differed between the benchmark groups in the "
        "current sample. The comparison is correlational and does not establish "
        "cause."
    )


def _build_recommendation(comparison, top, lower, overall_confidence):
    feature = comparison["feature"]
    label = comparison["label"]
    top_value = comparison["top_dominant_value"]
    user_value = comparison["user_value"]
    return {
        "title": _recommendation_title(feature, label),
        "evidence": (
            f"Top benchmarks were dominated by '{top_value}' "
            f"({top['count']} of {top['total']}), while lower benchmarks were "
            f"dominated by '{lower['value']}' ({lower['count']} of "
            f"{lower['total']}). The user intro was '{user_value}'."
        ),
        "why_it_matters": _why_it_matters(feature),
        "suggested_test": _suggested_test(feature, top_value, user_value),
        "confidence": _recommendation_confidence(
            top,
            lower,
            overall_confidence,
        ),
    }


def _final_verdict(comparisons, confidence):
    actionable = [item for item in comparisons if item["actionable"]]
    aligned = sum(item["status"] == "aligned_with_top" for item in actionable)
    missing = sum(
        item["status"] == "missing_winning_feature" for item in actionable
    )
    risks = sum(item["status"] == "risk_signal" for item in actionable)

    if confidence == "low":
        return "The available benchmark evidence is too limited for a clear position."
    if risks or missing:
        return (
            f"Across discriminative actionable features, the user intro aligns with "
            f"{aligned} top benchmark value(s), misses {missing}, and matches "
            f"{risks} lower benchmark value(s)."
        )
    if aligned:
        return (
            f"The user intro aligns with {aligned} discriminative actionable top "
            "benchmark value(s), with no supported risk signal."
        )
    return "No actionable feature had enough group contrast to position the intro."


def discover_patterns(top_features, lower_features, user_features):
    feature_comparison = []
    visual_comparisons = []
    storytelling_comparisons = []
    missing_winning_features = []
    risk_signals = []
    recommendation_inputs = []
    user_summary = _get_summary(user_features)

    for key, label in FEATURE_MAP.items():
        top = _dominant_value(_collect_values(top_features, key))
        lower = _dominant_value(_collect_values(lower_features, key))
        user_value = _normalize_value(user_summary.get(key))
        status = _comparison_status(key, user_value, top, lower)
        explanation = _comparison_explanation(
            label,
            user_value,
            top,
            lower,
            status,
        )
        comparison = {
            "feature": key,
            "label": label,
            "actionable": key in ACTIONABLE_FEATURES,
            "user_value": user_value,
            "top_dominant_value": top["value"],
            "top_evidence_count": top["count"],
            "top_evidence_total": top["total"],
            "top_evidence_share": top["share"],
            "top_evidence": _evidence_text("Top benchmarks", top),
            "lower_dominant_value": lower["value"],
            "lower_evidence_count": lower["count"],
            "lower_evidence_total": lower["total"],
            "lower_evidence_share": lower["share"],
            "lower_evidence": _evidence_text("Lower benchmarks", lower),
            "status": status,
            "explanation": explanation,
        }
        feature_comparison.append(comparison)
        if key in STORYTELLING_FEATURES:
            storytelling_comparisons.append(comparison)
        else:
            visual_comparisons.append(comparison)

        signal = {
            "feature": key,
            "label": label,
            "user_value": user_value,
            "top_dominant_value": top["value"],
            "lower_dominant_value": lower["value"],
            "evidence": (
                f"{_evidence_text('Top benchmarks', top)} "
                f"{_evidence_text('Lower benchmarks', lower)}"
            ),
            "explanation": explanation,
        }
        if status == "missing_winning_feature":
            missing_winning_features.append(signal)
        elif status == "risk_signal":
            risk_signals.append(signal)

        if status in {"missing_winning_feature", "risk_signal"}:
            recommendation_inputs.append((comparison, top, lower))

    confidence = _confidence(top_features, lower_features, feature_comparison)
    recommendations = [
        _build_recommendation(comparison, top, lower, confidence["level"])
        for comparison, top, lower in recommendation_inputs
    ]
    strongest_opportunities = missing_winning_features + risk_signals
    top_creator_experiments = recommendations[:3]

    return {
        "feature_comparison": feature_comparison,
        "visual_comparisons": visual_comparisons,
        "storytelling_comparisons": storytelling_comparisons,
        "user_position": [
            item["explanation"]
            for item in feature_comparison
            if item["actionable"] and item["status"] in POSITIONED_STATUSES
        ],
        "missing_winning_features": missing_winning_features,
        "risk_signals": risk_signals,
        "recommendations": recommendations,
        "strongest_opportunities": strongest_opportunities,
        "top_creator_experiments": top_creator_experiments,
        "final_verdict": _final_verdict(
            feature_comparison,
            confidence["level"],
        ),
        "confidence": confidence["level"],
        "confidence_reason": confidence["reason"],
    }