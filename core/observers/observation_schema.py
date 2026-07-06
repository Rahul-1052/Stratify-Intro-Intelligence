"""
Stratify Observation Schema

This module defines the canonical observation object used
throughout the Observation Layer.

Every observer returns this schema.

No networking.
No provider logic.
No recommendation logic.
"""

from copy import deepcopy


DEFAULT_OBSERVATION = {
    "opening_summary": "",
    "hook_type": "",
    "main_subject": "",
    "main_action": "",
    "setting": "",
    "visible_text": "",
    "emotion": "",
    "camera_framing": "",
    "central_conflict": "",
    "story_promise": "",
    "viewer_question": "",
    "possible_confusion": "",
    "first_impression": "",
    "confidence": "low",
}


def empty_observation():
    """Return a fresh observation object."""
    return deepcopy(DEFAULT_OBSERVATION)


def normalize_observation(observation):
    """
    Ensure every expected key exists.
    Ignore extra keys returned by providers.
    """

    result = empty_observation()

    if not isinstance(observation, dict):
        return result

    for key in result:
        value = observation.get(key)

        if value is not None:
            result[key] = str(value)

    return result


def build_intro_observation_response(
    status,
    observation,
    provider="",
    warnings=None,
):
    """
    Public response object returned by observe_intro().
    """

    return {
        "status": status,
        "provider": provider,
        "observation": normalize_observation(observation),
        "warnings": warnings or [],
    }