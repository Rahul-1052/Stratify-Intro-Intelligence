def _as_dict(value):
    return value if isinstance(value, dict) else {}


FIELD_LABELS = {
    "hook_visible_in_first_3_seconds": "early hook clarity",
    "subject_clarity": "subject clarity",
    "conflict_visible": "early conflict reveal",
    "payoff_teased": "payoff setup",
    "curiosity_gap": "curiosity gap",
    "opening_action_type": "opening action",
    "first_frame_strength": "first frame strength",
    "pacing_level": "intro pacing",
    "visual_energy": "visual energy",
    "human_presence": "human presence",
    "text_overlay": "visible text/context",
}


EXPERIMENTS = {
    "hook_visible_in_first_3_seconds": "Test making the hook clear within the first 3 seconds.",
    "subject_clarity": "Test making the main subject clear earlier in the intro.",
    "conflict_visible": "Test revealing the central conflict earlier.",
    "payoff_teased": "Test teasing the payoff earlier so viewers know what they are waiting for.",
    "curiosity_gap": "Test opening with a clearer unanswered question.",
    "opening_action_type": "Test starting with the type of action stronger benchmark intros use.",
    "first_frame_strength": "Test making the first frame more immediately understandable.",
    "pacing_level": "Test adjusting the intro pacing closer to stronger benchmark intros.",
    "visual_energy": "Test matching the visual energy level used by stronger benchmark intros.",
    "human_presence": "Test showing the main person or subject earlier if it fits the video.",
    "text_overlay": "Test using visible text earlier to clarify the setup.",
}


PRIORITY = (
    "hook_visible_in_first_3_seconds",
    "conflict_visible",
    "subject_clarity",
    "payoff_teased",
    "curiosity_gap",
    "first_frame_strength",
    "opening_action_type",
    "pacing_level",
    "visual_energy",
    "text_overlay",
    "human_presence",
)


def _choose_best_gap(field_comparisons):
    actionable = [
        item for item in field_comparisons
        if _as_dict(item).get("is_actionable_gap")
    ]

    if not actionable:
        return None

    priority_rank = {field: index for index, field in enumerate(PRIORITY)}

    actionable.sort(
        key=lambda item: (
            priority_rank.get(item.get("field"), 999),
            -_as_dict(item.get("top_pattern")).get("share", 0),
        )
    )

    return actionable[0]


def generate_recommendation(evidence, comparison):
    evidence = _as_dict(evidence)
    comparison = _as_dict(comparison)

    result = {
        "status": "no_recommendation",
        "confidence": "low",
        "what_stratify_saw": "",
        "what_successful_videos_did_differently": "",
        "next_best_experiment": "",
        "why_stratify_thinks_this": "",
        "evidence_trace": [],
        "warnings": [],
    }

    if comparison.get("status") != "success":
        result["what_stratify_saw"] = (
            "Stratify collected intro evidence, but the comparison was not strong enough."
        )
        result["why_stratify_thinks_this"] = comparison.get(
            "summary",
            "There was not enough evidence to support a recommendation.",
        )
        result["warnings"] = comparison.get("warnings", [])
        return result

    best_gap = _choose_best_gap(comparison.get("field_comparisons", []))

    if not best_gap:
        result["what_stratify_saw"] = (
            "Your intro does not show a clear evidence-backed weakness against the available benchmarks."
        )
        result["what_successful_videos_did_differently"] = (
            "The stronger benchmark intros did not show one consistent pattern that clearly separated them from weaker intros."
        )
        result["next_best_experiment"] = (
            "No strong experiment recommended yet. Run Stratify again with more benchmark evidence before changing the intro."
        )
        result["why_stratify_thinks_this"] = comparison.get("summary", "")
        result["warnings"] = comparison.get("warnings", [])
        return result

    field = best_gap.get("field")
    label = FIELD_LABELS.get(field, field.replace("_", " "))

    user_value = best_gap.get("user_value", "unknown")
    top_pattern = _as_dict(best_gap.get("top_pattern"))
    lower_pattern = _as_dict(best_gap.get("lower_pattern"))

    top_value = top_pattern.get("value", "unknown")
    lower_value = lower_pattern.get("value", "unknown")

    result["status"] = "recommendation_ready"
    result["confidence"] = comparison.get("confidence", "low")

    result["what_stratify_saw"] = (
        f"Stratify found that your intro's {label} is currently: {user_value}."
    )

    result["what_successful_videos_did_differently"] = (
        f"Stronger benchmark intros most often showed {label} as '{top_value}', "
        f"while weaker benchmark intros most often showed it as '{lower_value}'."
    )

    result["next_best_experiment"] = EXPERIMENTS.get(
        field,
        f"Test changing {label} closer to the stronger benchmark pattern.",
    )

    result["why_stratify_thinks_this"] = (
        f"This is recommended because {top_pattern.get('count', 0)} stronger benchmark intros "
        f"shared the same pattern for {label}, and your intro did not match that pattern."
    )

    result["evidence_trace"] = [
        {
            "field": field,
            "label": label,
            "user_value": user_value,
            "top_benchmark_pattern": top_pattern,
            "lower_benchmark_pattern": lower_pattern,
        }
    ]

    result["warnings"] = comparison.get("warnings", [])

    return result