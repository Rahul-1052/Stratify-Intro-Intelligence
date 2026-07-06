def _as_dict(value):
    return value if isinstance(value, dict) else {}


def _as_list(value):
    return value if isinstance(value, list) else []


COMPARISON_FIELDS = (
    "hook_visible_in_first_3_seconds",
    "subject_clarity",
    "conflict_visible",
    "payoff_teased",
    "curiosity_gap",
    "opening_action_type",
    "first_frame_strength",
    "pacing_level",
    "visual_energy",
    "human_presence",
    "text_overlay",
)


def _feature_summary(item):
    return _as_dict(_as_dict(item).get("feature_summary"))


def _successful_items(items):
    return [
        item for item in _as_list(items)
        if _as_dict(item).get("status") == "success"
    ]


def _count_values(items, field):
    counts = {}

    for item in items:
        value = _feature_summary(item).get(field, "unknown")
        if value in ("", None, "unknown"):
            continue

        counts[value] = counts.get(value, 0) + 1

    return counts


def _dominant_value(counts, total_count):
    if not counts or total_count <= 0:
        return {
            "value": "unknown",
            "count": 0,
            "share": 0,
            "is_consistent": False,
        }

    value, count = max(counts.items(), key=lambda pair: pair[1])
    share = count / total_count

    return {
        "value": value,
        "count": count,
        "share": round(share, 2),
        "is_consistent": share >= 0.6,
    }


def compare_benchmarks(evidence):
    evidence = _as_dict(evidence)

    user_intro = _as_dict(
        _as_dict(evidence.get("intro")).get("feature_summary")
    )

    benchmark = _as_dict(evidence.get("benchmark"))
    top_items = _successful_items(benchmark.get("top_performers"))
    lower_items = _successful_items(benchmark.get("lower_performers"))

    comparison = {
        "status": "success",
        "confidence": "low",
        "summary": "",
        "field_comparisons": [],
        "warnings": [],
    }

    if not user_intro:
        comparison["status"] = "insufficient_evidence"
        comparison["summary"] = "No usable intro evidence was found for the user's video."
        comparison["warnings"].append("User intro features are missing.")
        return comparison

    if len(top_items) < 2:
        comparison["status"] = "insufficient_evidence"
        comparison["summary"] = "Not enough successful benchmark intros were analyzed."
        comparison["warnings"].append("At least 2 top benchmark intros are needed.")
        return comparison

    if len(lower_items) < 1:
        comparison["warnings"].append(
            "Lower benchmark evidence is weak because few or no lower-performing intros were analyzed."
        )

    for field in COMPARISON_FIELDS:
        user_value = user_intro.get(field, "unknown")

        top_counts = _count_values(top_items, field)
        lower_counts = _count_values(lower_items, field)

        top_dominant = _dominant_value(top_counts, len(top_items))
        lower_dominant = _dominant_value(lower_counts, len(lower_items))

        user_matches_top = (
            user_value != "unknown"
            and user_value == top_dominant["value"]
            and top_dominant["is_consistent"]
        )

        user_matches_lower = (
            user_value != "unknown"
            and user_value == lower_dominant["value"]
            and lower_dominant["is_consistent"]
        )

        top_differs_from_lower = (
            top_dominant["value"] != "unknown"
            and lower_dominant["value"] != "unknown"
            and top_dominant["value"] != lower_dominant["value"]
        )

        field_result = {
            "field": field,
            "user_value": user_value,
            "top_pattern": top_dominant,
            "lower_pattern": lower_dominant,
            "user_matches_top": user_matches_top,
            "user_matches_lower": user_matches_lower,
            "top_differs_from_lower": top_differs_from_lower,
            "is_actionable_gap": (
                top_dominant["is_consistent"]
                and top_differs_from_lower
                and not user_matches_top
            ),
        }

        comparison["field_comparisons"].append(field_result)

    actionable = [
        item for item in comparison["field_comparisons"]
        if item["is_actionable_gap"]
    ]

    strong_patterns = [
        item for item in comparison["field_comparisons"]
        if item["top_pattern"]["is_consistent"]
    ]

    if len(top_items) >= 3 and len(lower_items) >= 2 and actionable:
        comparison["confidence"] = "moderate"
    elif len(top_items) >= 3 and strong_patterns:
        comparison["confidence"] = "low"
    else:
        comparison["confidence"] = "low"

    if actionable:
        comparison["summary"] = (
            "Stratify found at least one intro pattern where stronger benchmark videos "
            "behaved differently from weaker benchmark videos and the user's intro did not match the stronger pattern."
        )
    else:
        comparison["summary"] = (
            "Stratify did not find a strong enough benchmark difference to make a confident experiment."
        )

    return comparison