"""Evidence-only semantic comparison of free-form benchmark identities."""

import json
import re
from difflib import SequenceMatcher
from typing import Any, Mapping


CORE_FLOOR = 0.65
CORE_AVERAGE = 0.72
ASYMMETRY_LIMIT = 0.18


def compare_viewer_jobs(reference: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict:
    reference = _identity(reference)
    candidate = _identity(candidate)
    if not _complete(reference) or not _complete(candidate):
        return _limited("One or both evidence identities are incomplete.")

    first, provider = _judge(reference, candidate)
    if not first:
        return _limited("Viewer-job semantic comparison returned malformed evidence.")

    identity_alignment = _identity_alignment(reference, candidate)
    subject_alignment = _token_alignment(
        reference.get("subject", ""), candidate.get("subject", "")
    )
    assessment = _normalize(first)
    assessment["identity_alignment"] = identity_alignment
    assessment["subject_alignment"] = subject_alignment
    assessment["second_pass_used"] = False
    if _needs_second_pass(
        first, assessment, identity_alignment, subject_alignment
    ):
        adjudication_evidence = dict(first)
        adjudication_evidence["free_form_identity_alignment"] = identity_alignment
        adjudication_evidence["free_form_subject_alignment"] = subject_alignment
        second, second_provider = _judge(
            reference,
            candidate,
            prior_assessment=adjudication_evidence,
        )
        if second:
            assessment = _normalize(second)
            assessment["identity_alignment"] = identity_alignment
            assessment["subject_alignment"] = subject_alignment
            assessment["second_pass_used"] = True
            provider = second_provider or provider

    assessment.update({"status": "success", "provider": provider})
    return assessment


def _judge(reference, candidate, prior_assessment=None):
    adjudication = ""
    if prior_assessment:
        adjudication = f"""
This is one bounded adjudication pass. The first assessment was:
{json.dumps(prior_assessment, ensure_ascii=False)}
Resolve directional asymmetry or a borderline core decision. Do not merely
repeat the first answer. Keep source and presentation differences secondary to
the core viewer outcome and storytelling job.
If the first pass gave a high promised-outcome score while free-form subject
alignment is low, explicitly compare the non-entity action, event, or end-state
terms. A shared source or setting cannot compensate for a different payoff.
"""

    prompt = f"""
You are Stratify's benchmark qualification judge.

Compare two independently observed video identities. Decide whether a viewer
choosing one would reasonably consider the other an alternative for the same
desired experience or outcome.

Use only the supplied evidence. Do not use a predefined content taxonomy and
do not infer missing facts. Shared names, people, products, events, places, or
topics alone are insufficient.

Core decision:
- Viewer intent, promised outcome, and storytelling job are primary.
- Mentally remove shared named entities and check whether the remaining viewer
  outcome and narrative delivery mechanism are substitutes.
- A minor change in creator, source, location, subject instance, polish,
  technique, or presentation must not by itself make close substitutes
  incompatible.
- Treat demographic, location, creator, brand, and specific-instance details
  as subject attributes. After removing them, preserve compatibility when the
  desired viewer outcome and narrative mechanism still match.
- Treat "watch", "see", and "experience" as passive viewing unless the
  evidence explicitly says the viewer controls or participates in the event.
- Do not confuse people participating inside a recorded video with the viewer
  controlling or entering the event. A claim that the viewer "participates"
  is not sufficient without evidence of a direct input or reward mechanism
  outside ordinary playback. Treat the supplied identities as prerecorded
  viewing by default; wording in viewer_intent alone cannot prove interactivity.
- Different instances of the same activity remain substitutes when the viewer
  outcome and narrative mechanism are unchanged.
- A different instance is not a substitute when the specific promised event,
  payoff, or end state is itself the reason to watch. Sharing a source,
  setting, or story world does not preserve that payoff.
- Watching one process, event, or transformation unfold is not the same core
  job as learning a collection of suggestions, options, or commentary about it.
- If one identity promises a complete sequential outcome while the other
  samples independent advice or options, their expected completeness and
  narrative mechanism differ even when the learning topic is shared.
- General technique and producing a particular variant are substitutes only
  when the desired end state remains materially the same.
- If one presents an event or process directly and the other interprets,
  critiques, reacts to, summarizes, or reorganizes it for a different outcome,
  the core storytelling job is different.
- Score the core relationship in both directions. Material directional
  asymmetry must be visible in the directional scores.
- Presentation and source relationship affect confidence, not the core
  compatibility decision by themselves.

Score calibration:
- 0.80-1.00: same desired outcome and narrative mechanism, including different
  subject instances or sources only when the instance is not the promised payoff.
- 0.65-0.79: meaningful substitute with a narrower scope or modest mechanism
  difference.
- below 0.65: the desired outcome or narrative mechanism materially changes.
- The boolean and reason must agree with the four directional core scores.

Outcome relation calibration:
- "same": the candidate can satisfy the reference viewer's desired end state
  at the relevant level of abstraction. Different exercises, examples,
  implementations, or instances do not change this by themselves.
- "partial": the candidate satisfies a substantial but narrower portion of
  the desired end state.
- "different": completing or watching the candidate would leave the
  reference viewer's concrete desired end state unsatisfied.
- Describe the concrete outcomes without creator, brand, title, character,
  place, or other named-entity details unless that detail defines the payoff.

Reference identity:
{json.dumps(reference, ensure_ascii=False)}

Candidate identity:
{json.dumps(candidate, ensure_ascii=False)}
{adjudication}
Return only JSON:
{{
  "reference_promised_outcome": "concrete non-entity action or end state",
  "candidate_promised_outcome": "concrete non-entity action or end state",
  "outcome_relation": "same|partial|different",
  "reference_to_candidate": {{
    "viewer_intent_score": 0.0,
    "promised_outcome_score": 0.0,
    "storytelling_job_score": 0.0
  }},
  "candidate_to_reference": {{
    "viewer_intent_score": 0.0,
    "promised_outcome_score": 0.0,
    "storytelling_job_score": 0.0
  }},
  "presentation_compatibility": 0.0,
  "source_context_compatibility": 0.0,
  "same_viewing_job": false,
  "confidence": "low",
  "reason": ""
}}
"""
    from core.providers.provider_router import observe_text

    result = observe_text(prompt=prompt, timeout_seconds=25)
    if result.get("status") != "success":
        return {}, ""
    return _extract_json(result.get("content", "")), result.get("provider", "")


def _normalize(parsed):
    forward = parsed.get("reference_to_candidate") or {}
    reverse = parsed.get("candidate_to_reference") or {}
    fallback_intent = _score(parsed.get("viewer_intent_score"))
    fallback_outcome = _score(parsed.get("promised_outcome_score", fallback_intent))
    fallback_story = _score(parsed.get("storytelling_job_score"))
    forward_intent = _score(forward.get("viewer_intent_score", fallback_intent))
    reverse_intent = _score(reverse.get("viewer_intent_score", fallback_intent))
    forward_outcome = _score(
        forward.get("promised_outcome_score", forward_intent or fallback_outcome)
    )
    reverse_outcome = _score(
        reverse.get("promised_outcome_score", reverse_intent or fallback_outcome)
    )
    forward_story = _score(forward.get("storytelling_job_score", fallback_story))
    reverse_story = _score(reverse.get("storytelling_job_score", fallback_story))
    outcome_relation = str(parsed.get("outcome_relation") or "").strip().lower()
    raw_outcome_average = (forward_outcome + reverse_outcome) / 2
    outcome_relation_conflict = bool(
        (outcome_relation == "different" and raw_outcome_average >= 0.70)
        or (outcome_relation == "same" and raw_outcome_average < 0.65)
    )
    if outcome_relation_conflict:
        outcome_relation = "partial"
    if outcome_relation == "different":
        forward_outcome = min(forward_outcome, 0.49)
        reverse_outcome = min(reverse_outcome, 0.49)
    elif outcome_relation == "partial":
        forward_outcome = min(forward_outcome, 0.75)
        reverse_outcome = min(reverse_outcome, 0.75)
    viewer_intent = round((forward_intent + reverse_intent) / 2, 4)
    promised_outcome = round((forward_outcome + reverse_outcome) / 2, 4)
    storytelling = round((forward_story + reverse_story) / 2, 4)
    asymmetry = round(
        max(
            abs(forward_intent - reverse_intent),
            abs(forward_outcome - reverse_outcome),
            abs(forward_story - reverse_story),
        ),
        4,
    )
    core_values = (
        forward_intent,
        reverse_intent,
        forward_outcome,
        reverse_outcome,
        forward_story,
        reverse_story,
    )
    core_average = round(sum(core_values) / len(core_values), 4)
    same_job = min(core_values) >= CORE_FLOOR and core_average >= CORE_AVERAGE
    if same_job and min(core_values) >= 0.80 and asymmetry <= 0.10:
        confidence = "strong"
    elif same_job and min(core_values) >= 0.72 and asymmetry <= 0.16:
        confidence = "high"
    elif same_job:
        confidence = "moderate"
    else:
        confidence = "low"

    raw_reason = " ".join(str(parsed.get("reason") or "").split())
    if same_job:
        reason = (
            "Core viewer intent and storytelling job are compatible after "
            "removing shared named entities; presentation or source differences "
            "only reduce confidence."
        )
    else:
        reason = (
            f"Core compatibility {core_average:.2f} did not meet the required "
            f"viewer-intent and storytelling-job threshold after removing "
            f"shared named entities."
        )

    return {
        "viewer_intent_score": viewer_intent,
        "promised_outcome_score": promised_outcome,
        "promised_outcomes": {
            "reference": " ".join(
                str(parsed.get("reference_promised_outcome") or "").split()
            ),
            "candidate": " ".join(
                str(parsed.get("candidate_promised_outcome") or "").split()
            ),
            "relation": outcome_relation or "unavailable",
            "relation_conflict_resolved": outcome_relation_conflict,
        },
        "storytelling_job_score": storytelling,
        "presentation_compatibility": _score(parsed.get("presentation_compatibility")),
        "source_context_compatibility": _score(parsed.get("source_context_compatibility")),
        "same_viewing_job": same_job,
        "confidence": confidence,
        "reason": reason,
        "provider_reason_consistent": bool(raw_reason) and (
            bool(parsed.get("same_viewing_job")) == same_job
        ),
        "directional_scores": {
            "reference_to_candidate": {
                "viewer_intent_score": forward_intent,
                "promised_outcome_score": forward_outcome,
                "storytelling_job_score": forward_story,
            },
            "candidate_to_reference": {
                "viewer_intent_score": reverse_intent,
                "promised_outcome_score": reverse_outcome,
                "storytelling_job_score": reverse_story,
            },
        },
        "directional_asymmetry": asymmetry,
        "core_compatibility": core_average,
    }


def _needs_second_pass(
    parsed, assessment, identity_alignment=0.0, subject_alignment=0.0
):
    model_decision = bool(parsed.get("same_viewing_job"))
    return bool(
        assessment["directional_asymmetry"] > ASYMMETRY_LIMIT
        or model_decision != assessment["same_viewing_job"]
        or 0.65 <= assessment["core_compatibility"] <= 0.78
        or (
            identity_alignment >= 0.42
            and assessment["core_compatibility"] < CORE_AVERAGE
        )
        or (
            subject_alignment < 0.55
            and assessment["promised_outcome_score"] >= 0.80
        )
    )


def _identity_alignment(reference, candidate):
    scores = []
    for key in ("viewer_intent", "storytelling_format"):
        left = str(reference.get(key) or "").lower()
        right = str(candidate.get(key) or "").lower()
        if not left or not right:
            continue
        scores.append(_field_alignment(left, right))
    return round(sum(scores) / len(scores), 4) if scores else 0.0


def _field_alignment(left, right):
    left = str(left or "").lower()
    right = str(right or "").lower()
    if not left or not right:
        return 0.0
    left_tokens = set(re.findall(r"[a-z0-9]+", left))
    right_tokens = set(re.findall(r"[a-z0-9]+", right))
    union = left_tokens | right_tokens
    jaccard = len(left_tokens & right_tokens) / len(union) if union else 0.0
    sequence = SequenceMatcher(None, left, right).ratio()
    return round(max(jaccard, sequence), 4)


def _token_alignment(left, right):
    left_tokens = set(re.findall(r"[a-z0-9]+", str(left or "").lower()))
    right_tokens = set(re.findall(r"[a-z0-9]+", str(right or "").lower()))
    union = left_tokens | right_tokens
    return round(len(left_tokens & right_tokens) / len(union), 4) if union else 0.0


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
        "promised_outcome_score": 0.0,
        "storytelling_job_score": 0.0, "presentation_compatibility": 0.0,
        "source_context_compatibility": 0.0, "same_viewing_job": False,
        "confidence": "low", "reason": reason, "provider": "",
        "directional_scores": {}, "directional_asymmetry": 0.0,
        "core_compatibility": 0.0, "second_pass_used": False,
        "identity_alignment": 0.0, "subject_alignment": 0.0,
    }
