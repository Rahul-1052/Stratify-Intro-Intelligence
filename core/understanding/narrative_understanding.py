from typing import Any, Dict


def understand_narrative_intent(
    video: Dict[str, Any],
    vision: Dict[str, Any],
    intro_understanding: Dict[str, Any],
    transcript: str | None = None,
) -> Dict[str, Any]:
    """
    Explains what the intro appears to be trying to make the viewer understand.

    This module does not recommend.
    It translates evidence into narrative meaning.
    """

    title = video.get("title", "")
    description = video.get("description", "")

    events = intro_understanding.get("events", {}).get("events", [])
    temporal = intro_understanding.get("temporal", {})
    feature_summary = {
        "visual_energy": vision.get("visual_energy", "unknown"),
        "scene_type": vision.get("scene_type", "unknown"),
        "human_presence": vision.get("human_presence", "unknown"),
        "text_overlay": vision.get("text_overlay", "unknown"),
    }

    return {
        "status": "success",
        "main_subject": _infer_subject(title, description),
        "opening_goal": _infer_opening_goal(title, events, feature_summary),
        "viewer_expectation": _infer_viewer_expectation(title, feature_summary),
        "story_promise": _infer_story_promise(title, description),
        "unanswered_question": _infer_unanswered_question(title),
        "narrative_progression": temporal.get("summary", "Temporal flow unavailable."),
        "evidence_used": {
            "title": title,
            "event_count": len(events),
            "feature_summary": feature_summary,
        },
        "confidence": "limited",
    }


def _infer_subject(title: str, description: str) -> str:
    if title:
        return title
    if description:
        return description[:120]
    return "unknown"


def _infer_opening_goal(title, events, feature_summary):
    energy = feature_summary.get("visual_energy")

    if events:
        return "The intro appears to establish the opening situation through observable visual changes."

    if energy in {"high", "medium"}:
        return "The intro appears to rely on visual movement to create attention."

    return "The opening goal is unclear from current evidence."


def _infer_viewer_expectation(title, feature_summary):
    if feature_summary.get("human_presence") is True:
        return "The viewer likely expects the visible subject to create meaning or momentum."

    return "The viewer expectation is unclear from current evidence."


def _infer_story_promise(title: str, description: str) -> str:
    if title:
        return f"The title promises: {title}"

    if description:
        return f"The description suggests: {description[:160]}"

    return "No clear story promise was available."


def _infer_unanswered_question(title: str) -> str:
    if title:
        return f"What makes '{title}' worth continuing to watch?"

    return "What happens next?"
