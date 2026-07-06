EXPERIMENT_TEMPLATES = {
    "opening_momentum": [
        {
            "title": "Start closer to the first meaningful event",
            "experiment": (
                "Create a version where the first few seconds begin nearer to the action, "
                "conflict, or decision point instead of spending time on setup."
            ),
        },
        {
            "title": "Make the hook visible earlier",
            "experiment": (
                "Move the clearest hook into the opening moments so the viewer understands "
                "why the scene matters sooner."
            ),
        },
    ],
    "story_clarity": [
        {
            "title": "Reveal the conflict earlier",
            "experiment": (
                "Test an opening where the central tension or problem is visible before extra context is explained."
            ),
        },
        {
            "title": "Hint at the payoff sooner",
            "experiment": (
                "Add an early signal of what the viewer will get if they keep watching."
            ),
        },
    ],
    "visual_engagement": [
        {
            "title": "Increase visual change in the opening",
            "experiment": (
                "Test a version with more visible movement, shot variation, or faster visual progression "
                "during the first few seconds."
            ),
        },
        {
            "title": "Open with a more active visual moment",
            "experiment": (
                "Try beginning with a frame or moment that already contains movement, action, or visual tension."
            ),
        },
    ],
}


def generate_experiments(insights, max_experiments=6):
    experiments = []

    for insight in insights:
        templates = EXPERIMENT_TEMPLATES.get(insight["id"], [])

        for template in templates:
            experiments.append(
                {
                    "title": template["title"],
                    "experiment": template["experiment"],
                    "linked_insight": insight["title"],
                    "confidence": insight["confidence"],
                    "why": insight["summary"],
                    "evidence": [
                        {
                            "label": item.get("label"),
                            "user_value": item.get("user_value"),
                            "top_value": item.get("top_dominant_value"),
                            "lower_value": item.get("lower_dominant_value"),
                            "explanation": item.get("explanation"),
                        }
                        for item in insight.get("evidence", [])[:4]
                    ],
                }
            )

    confidence_rank = {"high": 0, "moderate": 1, "low": 2}

    experiments = sorted(
        experiments,
        key=lambda item: confidence_rank.get(item.get("confidence", "low"), 2),
    )

    return experiments[:max_experiments]