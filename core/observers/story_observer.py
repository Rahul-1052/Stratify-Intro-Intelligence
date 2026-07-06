"""
Stratify Story Observer

Deterministic story interpretation from visual observation.

No AI calls.
No provider calls.
No recommendations.
"""

from core.observers.observation_schema import normalize_observation


def observe_story(observation):
    observation = normalize_observation(observation)

    updates = {}

    if not observation.get("hook_type"):
        if observation.get("main_action"):
            updates["hook_type"] = "action"
        else:
            updates["hook_type"] = "unknown"

    if not observation.get("central_conflict"):
        updates["central_conflict"] = "unknown"

    if not observation.get("story_promise"):
        if observation.get("main_subject") and observation.get("main_action"):
            updates["story_promise"] = (
                f"The intro sets up {observation['main_subject']} through "
                f"{observation['main_action']}."
            )
        else:
            updates["story_promise"] = "unknown"

    if not observation.get("viewer_question"):
        if observation.get("central_conflict") not in ["", "unknown"]:
            updates["viewer_question"] = "How will this conflict develop?"
        else:
            updates["viewer_question"] = "unknown"

    return updates