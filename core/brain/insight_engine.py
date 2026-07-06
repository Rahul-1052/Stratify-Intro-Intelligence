INSIGHT_GROUPS = {
    "opening_momentum": {
        "title": "Opening Momentum",
        "features": {
            "pacing_level",
            "opening_action_type",
            "hook_visible_in_first_3_seconds",
            "scene_changes",
            "scene_change_count",
        },
        "creator_meaning": "How quickly the video begins feeling active and worth watching.",
    },
    "story_clarity": {
        "title": "Story Clarity",
        "features": {
            "conflict_visible",
            "payoff_teased",
            "curiosity_gap",
            "subject_clarity",
            "first_frame_strength",
        },
        "creator_meaning": "How quickly a viewer understands what is happening and why it matters.",
    },
    "visual_engagement": {
        "title": "Visual Engagement",
        "features": {
            "visual_energy",
            "motion_level",
            "scene_type",
            "human_presence",
            "text_overlay",
        },
        "creator_meaning": "How visually active or engaging the opening feels.",
    },
}


def _is_actionable(item):
    if not isinstance(item, dict):
        return False

    if not item.get("actionable"):
        return False

    status = str(item.get("status", "")).lower()

    return status in {
        "missing_winning_feature",
        "risk_signal",
        "worth_testing",
    } or (
        item.get("top_dominant_value")
        and item.get("lower_dominant_value")
        and str(item.get("user_value")).lower()
        == str(item.get("lower_dominant_value")).lower()
        and str(item.get("user_value")).lower()
        != str(item.get("top_dominant_value")).lower()
    )


def _confidence(items):
    if not items:
        return "low"

    strong = 0
    for item in items:
        top_count = item.get("top_evidence_count", 0) or 0
        lower_count = item.get("lower_evidence_count", 0) or 0
        if top_count >= 2 and lower_count >= 2:
            strong += 1

    if strong >= 3:
        return "high"
    if strong >= 1:
        return "moderate"
    return "low"


def _summary_for_group(title, items):
    if title == "Opening Momentum":
        return (
            "The opening appears slower or more setup-heavy than stronger benchmark intros."
        )
    if title == "Story Clarity":
        return (
            "The opening may not reveal the core conflict, payoff, or viewer question early enough."
        )
    if title == "Visual Engagement":
        return (
            "The opening appears visually calmer than stronger benchmark intros."
        )
    return "This area showed a meaningful difference against stronger benchmark intros."


def generate_insights(patterns):
    comparisons = patterns.get("feature_comparison", []) if isinstance(patterns, dict) else []

    grouped = []

    for group_key, config in INSIGHT_GROUPS.items():
        matched_items = [
            item
            for item in comparisons
            if item.get("feature") in config["features"] and _is_actionable(item)
        ]

        if not matched_items:
            continue

        grouped.append(
            {
                "id": group_key,
                "title": config["title"],
                "summary": _summary_for_group(config["title"], matched_items),
                "creator_meaning": config["creator_meaning"],
                "confidence": _confidence(matched_items),
                "evidence_count": len(matched_items),
                "evidence": matched_items,
            }
        )

    return grouped