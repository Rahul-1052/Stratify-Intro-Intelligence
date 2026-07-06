import json
import re

from core.providers.provider_router import observe_visual
from core.observers.observation_schema import (
    normalize_observation,
    build_intro_observation_response,
)


def _extract_json(text):
    text = str(text or "").strip()
    text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^```", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return {}

    try:
        return json.loads(text[start : end + 1])
    except Exception:
        return {}


def _build_prompt(video=None):
    video = video or {}
    title = str(video.get("title", "") or "")[:180]

    return f"""
You are Stratify's Literal Visual Observer.

Look at these sampled intro frames from a YouTube video.

Video title for light context:
{title}

Your job is ONLY to describe what is visible.

Do NOT recommend.
Do NOT predict views.
Do NOT predict retention.
Do NOT explain performance.
Do NOT invent unseen details.

Return ONLY valid JSON:

{{
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
  "confidence": "low"
}}

Rules:
- If uncertain, say "unknown".
- visible_text must be only readable text from frames, or "none visible".
- confidence must be high, moderate, or low.
- Keep every field short.
"""


def observe_visual_intro(frame_data_urls, video=None, timeout_seconds=30):
    if not frame_data_urls:
        return build_intro_observation_response(
            status="unavailable",
            observation={},
            provider="",
            warnings=["No frames available for visual observation."],
        )

    provider_result = observe_visual(
        prompt=_build_prompt(video),
        frame_data_urls=frame_data_urls,
        timeout_seconds=timeout_seconds,
    )

    if provider_result.get("status") != "success":
        return build_intro_observation_response(
            status="unavailable",
            observation={},
            provider=provider_result.get("provider", ""),
            warnings=provider_result.get("warnings")
            or [provider_result.get("warning", "Visual observation unavailable.")],
        )

    parsed = _extract_json(provider_result.get("content", ""))

    if not parsed:
        return build_intro_observation_response(
            status="unavailable",
            observation={},
            provider=provider_result.get("provider", ""),
            warnings=[
                "Visual provider responded, but did not return valid JSON.",
                provider_result.get("content", "")[:500],
            ],
        )

    return build_intro_observation_response(
        status="success",
        observation=normalize_observation(parsed),
        provider=provider_result.get("provider", ""),
        warnings=provider_result.get("warnings", []),
    )