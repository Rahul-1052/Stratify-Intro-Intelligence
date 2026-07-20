"""Translate structured intro evidence into honest creator-facing reasoning."""

from typing import Any, Dict, List, Mapping


UNKNOWN = {"", "unknown", "none", "n/a", "unavailable", "not detected"}


def _text(value):
    if value is None or isinstance(value, (dict, list, tuple, set)):
        return ""
    value = str(value).strip()
    return "" if value.lower() in UNKNOWN else value


def _first(mapping, *keys):
    mapping = mapping if isinstance(mapping, Mapping) else {}
    for key in keys:
        value = _text(mapping.get(key))
        if value:
            return value
    return ""


def _evidence(report):
    intro = report.get("intro_observation") or {}
    observation = intro.get("observation") or intro.get("observations") or {}
    features = (report.get("feature_report") or {}).get("feature_summary") or {}
    frames = (report.get("vision") or {}).get("frame_observations") or []
    return observation if isinstance(observation, Mapping) else {}, features, frames


def _viewer_snapshot(observation, features, frames):
    subject = _first(observation, "main_subject", "subject_clarity") or _first(features, "main_subject")
    hook = _first(observation, "hook_type", "opening_action_type") or _first(features, "hook_type", "opening_mode")
    promise = _first(observation, "story_promise", "payoff_teased", "viewer_question")
    setting = next((_text(frame.get("scene_type")) for frame in frames if _text(frame.get("scene_type"))), "")
    sentences = []
    if subject:
        sentences.append(f"The viewer first meets {subject}.")
    elif setting:
        sentences.append(f"The opening first places the viewer in {setting}.")
    else:
        summary = _first(observation, "opening_summary", "first_impression")
        if summary:
            sentences.append(summary.rstrip(".") + ".")
    if hook:
        sentences.append(f"The first beat is built around {hook}, which gives the viewer an immediate idea to follow.")
    if promise:
        sentences.append(f"The opening points toward {promise}, giving the sequence a clear direction.")
    if not sentences:
        return "The available intro evidence is too limited to describe the first viewer experience without guessing."
    return " ".join(sentences[:3])


def _moment_sentence(frame, previous):
    scene = _text(frame.get("scene_type"))
    previous_scene = _text((previous or {}).get("scene_type"))
    if frame.get("text_overlay") is True and (previous or {}).get("text_overlay") is not True:
        return "A written message adds context, giving the viewer another cue for how to read the opening."
    if scene and previous_scene and scene != previous_scene:
        return "The setting or composition shifts, creating a new beat in the introduction."
    if frame.get("human_presence") is True and (previous or {}).get("human_presence") is not True:
        return "The on-screen subject enters the sequence, giving the viewer a clear point of focus."
    energy = _text(frame.get("visual_energy")).lower()
    previous_energy = _text((previous or {}).get("visual_energy")).lower()
    if energy == "high" and previous_energy != "high":
        return "The sequence becomes more active, increasing the sense that the opening is moving somewhere."
    if not previous:
        if scene:
            return f"The opening establishes {scene}, so the viewer can quickly understand where the video begins."
        return "The first image establishes the starting point for the sequence."
    return "The opening holds its current idea long enough for the viewer to take in the setup."


def _creative_timeline(frames, observation):
    if not frames:
        summary = _first(observation, "opening_summary", "first_impression")
        return [{"time": "Opening", "moment": summary or "The sequence could not be broken into honest creative moments from the available evidence."}]
    ordered = sorted(frames, key=lambda item: float(item.get("timestamp", 0) or 0))[:8]
    moments = []
    previous = None
    for index, frame in enumerate(ordered):
        start = float(frame.get("timestamp", index) or 0)
        end = float(ordered[index + 1].get("timestamp", start + 1) or start + 1) if index + 1 < len(ordered) else start + 1
        sentence = _moment_sentence(frame, previous)
        if not moments or moments[-1]["moment"] != sentence:
            moments.append({"time": f"{start:.0f}-{end:.0f}s", "moment": sentence})
        previous = frame
    return moments[:6]


def _insight(observation, interpretation, recommendation, reason, title, constant, comparison, evidence_key):
    values = (observation, interpretation, recommendation, reason, title, constant, comparison, evidence_key)
    if not all(_text(value) for value in values):
        return None
    return {
        "title": title,
        "observation": observation,
        "interpretation": interpretation,
        "recommendation": recommendation,
        "reason": reason,
        "what_stays_constant": constant,
        "how_to_compare": comparison,
        "source": "Observation-backed",
        "evidence_key": evidence_key,
        "benchmark_supported": False,
    }


def _observation_insights(observation, features, frames):
    subject = _first(observation, "main_subject", "subject_clarity") or _first(features, "main_subject")
    hook = _first(observation, "hook_type", "opening_action_type") or _first(features, "hook_type", "opening_mode")
    promise = _first(observation, "story_promise", "payoff_teased", "viewer_question")
    has_written_context = any(frame.get("text_overlay") is True for frame in frames)
    scene_shift = any(
        _text(frame.get("scene_type")) and _text(previous.get("scene_type")) and _text(frame.get("scene_type")) != _text(previous.get("scene_type"))
        for previous, frame in zip(frames, frames[1:])
    )
    candidates = []
    if subject:
        candidates.append(_insight(
            f"The opening gives {subject} the central role.",
            "That focus helps the viewer understand what to pay attention to before more information arrives.",
            "Create one alternate cut where the subject fills the first frame more decisively.",
            "Testing the framing isolates whether the central idea can be understood faster without changing the content itself.",
            "Make the first frame choose a clear subject", "Keep the dialogue, music, shot order, and total intro length unchanged.",
            "Show both first frames without the title and ask which one communicates the subject more quickly.", "main_subject",
        ))
    if hook:
        candidates.append(_insight(
            f"The opening is organized around {hook}.",
            "This gives the viewer a starting idea, but its placement determines how quickly the video feels underway.",
            "Move the clearest expression of that hook into the first two seconds.",
            "The test reveals whether earlier context makes the same opening easier to follow.",
            "Bring the core hook forward", "Keep the hook itself, the footage selection, and the overall intro duration unchanged.",
            "Compare how quickly a first-time viewer can describe what the video is setting up.", "hook_type",
        ))
    if promise:
        candidates.append(_insight(
            f"The opening points toward {promise}.",
            "A visible destination gives the viewer a reason to understand how the opening moments connect.",
            "Build a second version that states or shows that destination in one concise first-beat cue.",
            "The test checks whether the video's direction is clear without adding a new promise.",
            "State the destination in one beat", "Keep the promised outcome, footage, music, and total duration unchanged.",
            "Watch both versions once and compare which makes the video's destination easier to summarize.", "story_promise",
        ))
    if has_written_context:
        candidates.append(_insight(
            "A written message enters during the opening.",
            "That message competes with the imagery for attention, so its hierarchy determines whether it clarifies or crowds the beat.",
            "Create one version that reduces the message to a single short line.",
            "Changing only the wording tests whether the same context can be understood with less reading effort.",
            "Reduce the opening message to one line", "Keep its timing, type style, footage, audio, and intro length unchanged.",
            "Compare which version lets a viewer repeat the message accurately after one watch.", "text_overlay",
        ))
    if scene_shift:
        candidates.append(_insight(
            "The opening introduces a distinct second beat after the initial setup.",
            "That progression gives the sequence direction instead of leaving the first idea static.",
            "Create an alternate cut that starts the second beat one second earlier.",
            "Moving only the transition tests whether the setup reaches its first development more efficiently.",
            "Test the timing of the second beat", "Keep every shot, the audio, and the endpoint of the intro unchanged.",
            "Compare which cut makes the progression from setup to development easier to notice.", "scene_transition",
        ))
    return [item for item in candidates if item]


def _strengths(observation, features, frames):
    strengths = []
    subject = _first(observation, "main_subject", "subject_clarity") or _first(features, "main_subject")
    promise = _first(observation, "story_promise", "payoff_teased", "viewer_question")
    hook = _first(observation, "hook_type", "opening_action_type") or _first(features, "hook_type", "opening_mode")
    if subject:
        strengths.append({"title": "A clear point of focus", "explanation": f"By centering {subject}, the opening gives the viewer an immediate idea to organize the scene around."})
    if hook:
        strengths.append({"title": "The opening has a defined first beat", "explanation": f"Building the start around {hook} gives the sequence a recognizable entry point rather than an unrelated preamble."})
    if promise:
        strengths.append({"title": "The sequence points somewhere", "explanation": f"The promise of {promise} connects the opening to a destination the viewer can understand."})
    if any(frame.get("text_overlay") is True for frame in frames):
        strengths.append({"title": "Context is available without audio", "explanation": "The written cue helps communicate the setup even when the opening is watched silently."})
    return strengths[:3]


def build_creative_reasoning(report):
    observation, features, frames = _evidence(report)
    insights = _observation_insights(observation, features, frames)
    strengths = _strengths(observation, features, frames)
    priority = insights[0] if insights else None
    return {
        "status": "success" if observation or features or frames else "limited",
        "opening_snapshot": _viewer_snapshot(observation, features, frames),
        "timeline": _creative_timeline(frames, observation),
        "strengths": strengths,
        "insights": insights,
        "priority": priority,
        "experiments": insights[:3],
        "evidence_count": len(observation) + len(features) + len(frames),
    }
