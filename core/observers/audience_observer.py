"""
Stratify Audience Observer

Deterministic first-time viewer interpretation.

No AI calls.
No provider calls.
No recommendations.
"""

from core.observers.observation_schema import normalize_observation


def observe_audience(observation):
    observation = normalize_observation(observation)

    updates = {}

    if not observation.get("possible_confusion"):
        unclear_parts = []

        if observation.get("main_subject") in ["", "unknown"]:
            unclear_parts.append("main subject")

        if observation.get("central_conflict") in ["", "unknown"]:
            unclear_parts.append("central conflict")

        if unclear_parts:
            updates["possible_confusion"] = (
                "A first-time viewer may not immediately understand the "
                + " and ".join(unclear_parts)
                + "."
            )
        else:
            updates["possible_confusion"] = "none obvious"

    if not observation.get("first_impression"):
        if observation.get("opening_summary"):
            updates["first_impression"] = observation["opening_summary"]
        else:
            updates["first_impression"] = "The intro is visually available, but the first impression is unclear."

    return updates