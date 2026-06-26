def compare_intro_observations(user_observation, top_observations=None, lower_observations=None):
    """
    Semantic comparison layer.

    Responsibility:
    Compare VLM intro observations across user, top benchmarks, and lower benchmarks.
    Do not recommend.
    Do not claim causation.
    """

    return {
        "status": "not_ready",
        "semantic_differences": [],
        "user_position": [],
        "warnings": ["Semantic comparison is not connected yet."],
    }