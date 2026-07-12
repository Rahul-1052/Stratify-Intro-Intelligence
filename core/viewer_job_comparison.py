"""Evidence-only semantic comparison of free-form benchmark identities."""

import json
import re
from typing import Any, Mapping

def compare_viewer_jobs(reference: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict:
    reference = _identity(reference)
    candidate = _identity(candidate)
    if not _complete(reference) or not _complete(candidate):
        return _limited("One or both evidence identities are incomplete.")

    prompt = f"""
You are Stratify's benchmark qualification judge.

Compare two independently observed video identities. Decide whether they serve
the same viewing job: a viewer choosing one would reasonably consider the other
an alternative for the same desired experience or outcome.

Use only the supplied evidence. Shared subject names alone are insufficient.
Do not use a predefined content taxonomy. Do not infer missing facts.

Reference identity:
{json.dumps(reference, ensure_ascii=False)}

Candidate identity:
{json.dumps(candidate, ensure_ascii=False)}

Return only JSON:
{{
  "viewer_intent_score": 0.0,
  "storytelling_job_score": 0.0,
  "presentation_compatibility": 0.0,
  "source_context_compatibility": 0.0,
  "same_viewing_job": false,
  "confidence": "low",
  "reason": ""
}}

Scores must be between 0 and 1. same_viewing_job may be true only when both
viewer intent and storytelling job are strongly supported. Presentation style
may vary, but commentary about an event and direct presentation of that event
are not automatically the same viewing job.
"""
    from core.providers.provider_router import observe_text

    result = observe_text(prompt=prompt, timeout_seconds=25)
    if result.get("status") != "success":
        return _limited("Viewer-job semantic comparison provider was unavailable.")

    parsed = _extract_json(result.get("content", ""))
    if not parsed:
        return _limited("Viewer-job semantic comparison returned malformed evidence.")

    viewer_intent = _score(parsed.get("viewer_intent_score"))
    storytelling = _score(parsed.get("storytelling_job_score"))
    same_job = bool(parsed.get("same_viewing_job")) and min(viewer_intent, storytelling) >= 0.60
    return {
        "status": "success",
        "viewer_intent_score": viewer_intent,
        "storytelling_job_score": storytelling,
        "presentation_compatibility": _score(parsed.get("presentation_compatibility")),
        "source_context_compatibility": _score(parsed.get("source_context_compatibility")),
        "same_viewing_job": same_job,
        "confidence": str(parsed.get("confidence") or "low").strip().lower(),
        "reason": " ".join(str(parsed.get("reason") or "").split()),
        "provider": result.get("provider", ""),
    }


def _identity(value):
    return {
        key: " ".join(str((value or {}).get(key) or "").split())
        for key in (
            "subject", "viewer_intent", "presentation_style",
            "storytelling_format", "source_context",
        )
    }


def _complete(identity):
    return bool(identity.get("viewer_intent") and identity.get("storytelling_format"))


def _extract_json(text):
    text = re.sub(r"^```(?:json)?", "", str(text or "").strip(), flags=re.I).strip()
    text = re.sub(r"```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        return json.loads(text[start:end + 1])
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _score(value):
    try:
        return round(max(0.0, min(float(value), 1.0)), 4)
    except (TypeError, ValueError):
        return 0.0


def _limited(reason):
    return {
        "status": "limited", "viewer_intent_score": 0.0,
        "storytelling_job_score": 0.0, "presentation_compatibility": 0.0,
        "source_context_compatibility": 0.0, "same_viewing_job": False,
        "confidence": "low", "reason": reason, "provider": "",
    }
