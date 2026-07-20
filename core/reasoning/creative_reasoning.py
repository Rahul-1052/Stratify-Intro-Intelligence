"""Creator-facing reasoning derived exclusively from Semantic Observation V2."""

from core.observers.semantic_observer import observe_semantics


def _semantic_input(report):
    semantic = report.get("semantic_observation") or {}
    if semantic.get("version") == "observation-semantics-v2":
        return semantic
    frames = (report.get("vision") or {}).get("frame_observations") or []
    return observe_semantics(frames)


def _insight(title, observation, interpretation, recommendation, reason, constant, comparison, evidence_key, confidence):
    values = (title, observation, interpretation, recommendation, reason, constant, comparison, evidence_key)
    if not all(str(value or "").strip() for value in values):
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
        "confidence": confidence,
        "benchmark_supported": False,
    }


def _focus_insight(semantic):
    focus = semantic["primary_visual_focus"]
    clarity = semantic["focus_clarity"]
    confidence = semantic["semantic_confidence"]
    if focus == "unavailable" or clarity == "unavailable":
        return None
    if clarity == "competing":
        return _insight(
            "Give the first frame one clear owner",
            "More than one element competes to lead the opening composition.",
            "The viewer has to divide attention before a stable hierarchy is established.",
            "Create one alternate first frame containing only the intended dominant subject.",
            "Removing one source of competition tests whether the opening idea becomes easier to identify.",
            "Keep the audio, duration, following shots, color treatment, and message unchanged.",
            "Show both first frames without context and compare which produces a more consistent description of the main focus.",
            "focus_clarity:competing", confidence,
        )
    if clarity in {"delayed", "develops_early"}:
        return _insight(
            "Establish the visual priority sooner",
            "A stable dominant subject emerges only after the opening has already begun.",
            "The early frames provide context before they provide a singular point of focus.",
            "Move the first frame with a clear dominant subject to the start of the sequence.",
            "Changing only the order tests whether the opening hierarchy becomes legible sooner.",
            "Keep every frame, the audio, total duration, and written message unchanged.",
            "Compare the first two seconds and note which version reveals one dominant focus earlier.",
            f"focus_clarity:{clarity}", confidence,
        )
    return _insight(
        "Protect the opening's clear hierarchy",
        "One dominant visual focus is established in the first beat.",
        "A singular starting point makes the opening composition easy to parse before later elements arrive.",
        "Create one alternate first frame with one secondary element removed.",
        "The controlled subtraction tests which supporting element can disappear without weakening the opening hierarchy.",
        "Keep the dominant subject, audio, timing, color, and following edit unchanged.",
        "Compare which frame preserves the same main focus with less competing information.",
        "focus_clarity:immediate", confidence,
    )


def _text_insight(semantic):
    role = semantic["text_role"]
    mode = semantic["information_mode"]
    confidence = semantic["semantic_confidence"]
    if role in {"unavailable", "absent"}:
        return None
    if role in {"persistent", "dominant"}:
        return _insight(
            "Give the image a text-free first beat",
            "Written information occupies most or all of the sampled opening.",
            "The wording and imagery must be processed together before either can lead cleanly.",
            "Delay the written cue until the second semantic beat.",
            "Changing only its entrance tests whether the image can establish context before reading begins.",
            "Keep the wording, typography, footage, audio, and total intro duration unchanged.",
            "Compare which version makes the main visual focus easier to identify before reading the message.",
            f"text_role:{role}", confidence,
        )
    return _insight(
        "Test the timing of the written cue",
        "Written context appears for part of the opening while imagery remains present.",
        "Its entrance creates a separate information beat and temporarily shares attention with the image.",
        "Move the written cue one beat later in an alternate cut.",
        "The timing test shows whether the image benefits from establishing itself before the message arrives.",
        "Keep the wording, screen position, footage, audio, and total duration unchanged.",
        "Compare when the main visual focus becomes clear in each version and whether the message remains understandable.",
        f"information_mode:{mode};text_role:{role}", confidence,
    )


def _progression_insight(semantic):
    progression = semantic["visual_progression"]
    confidence = semantic["semantic_confidence"]
    if progression == "unavailable":
        return None
    if progression == "mostly_held":
        return _insight(
            "Create a deliberate second beat",
            "The sampled opening remains on one semantic setup.",
            "The viewer receives a stable composition, but the sequence offers no clearly separate development within the sample.",
            "Introduce one existing alternate composition at the midpoint of the opening.",
            "Adding one controlled development tests whether the setup benefits from a clearer sense of progression.",
            "Keep the subject, message, audio, opening frame, and total duration unchanged.",
            "Compare whether the alternate cut communicates two distinct beats without making the opening harder to follow.",
            "visual_progression:mostly_held", confidence,
        )
    if progression == "frequent_change":
        return _insight(
            "Let one opening composition carry more weight",
            "The opening moves through many materially different semantic beats in a short span.",
            "No single setup receives much time to establish the visual hierarchy before the next one arrives.",
            "Remove one early composition and extend the clearest remaining beat by the same duration.",
            "The test isolates whether fewer beats make the sequence easier to parse without slowing its total runtime.",
            "Keep the audio, main subject, message, endpoint, and total intro duration unchanged.",
            "Compare which version produces a clearer account of the opening sequence after one silent viewing.",
            "visual_progression:frequent_change", confidence,
        )
    return _insight(
        "Test where the first development begins",
        "The opening contains more than one clearly separated semantic beat.",
        "The transition between setup and development defines how long the first composition carries the opening alone.",
        "Move the start of the second beat one second earlier in an alternate cut.",
        "Changing only the transition timing tests whether the progression becomes clearer without adding new material.",
        "Keep the frames, audio, message, order, and total intro duration unchanged.",
        "Compare which cut makes the shift from setup to development easier to identify.",
        f"visual_progression:{progression}", confidence,
    )


def _subject_pattern_insight(semantic):
    pattern = semantic["subject_presence_pattern"]
    confidence = semantic["semantic_confidence"]
    if pattern in {"unavailable", "present_immediately"}:
        return None
    if pattern == "multiple_subjects":
        return _insight(
            "Separate competing figures in the first beat",
            "Several figures share visual priority during the opening.",
            "The composition does not provide one singular figure for the viewer to use as an anchor.",
            "Crop or reframe one alternate first beat so only one figure carries visual priority.",
            "The framing test checks whether a singular anchor makes the opening hierarchy more decisive.",
            "Keep the footage moment, audio, duration, color, and following edit unchanged.",
            "Compare which framing produces more agreement about where attention should begin.",
            "subject_presence_pattern:multiple_subjects", confidence,
        )
    return _insight(
        "Make the subject entrance intentional",
        "A central figure appears after the opening begins or is not maintained consistently.",
        "The sequence changes from context-led to subject-led, creating a meaningful handoff in visual priority.",
        "Create an alternate cut that holds the context until the subject entrance, with no intervening composition.",
        "Removing the intermediate beat tests whether the handoff to the subject becomes easier to read.",
        "Keep the subject entrance frame, audio, message, endpoint, and total duration unchanged.",
        "Compare which version makes the moment of subject introduction more distinct.",
        f"subject_presence_pattern:{pattern}", confidence,
    )


def _strengths(semantic):
    strengths = []
    if semantic["focus_clarity"] == "immediate":
        strengths.append({"title": "The hierarchy is clear immediately", "explanation": "One visual focus leads from the first beat, so the opening does not ask the viewer to resolve competing elements before understanding where to look."})
    if semantic["subject_presence_pattern"] == "present_immediately" and semantic["visual_progression"] in {"gradual_change", "distinct_beats"}:
        strengths.append({"title": "The opening changes without losing its anchor", "explanation": "The same central figure carries across multiple beats, giving the edit progression while preserving continuity."})
    if semantic["information_mode"] == "image_and_text" and semantic["text_role"] == "intermittent":
        strengths.append({"title": "Written context has a defined moment", "explanation": "The written cue enters as one part of the sequence rather than replacing the imagery throughout the entire opening."})
    if semantic["opening_mode"] == "environment_first" and semantic["focus_clarity"] in {"immediate", "develops_early"}:
        strengths.append({"title": "Context arrives before detail", "explanation": "The environment establishes where the sequence begins before the edit asks a more specific subject to carry attention."})
    return strengths


def _priority(insights):
    priority_order = ("competing", "delayed", "persistent", "dominant", "frequent_change", "mostly_held")
    for term in priority_order:
        for insight in insights:
            if term in insight["evidence_key"]:
                return insight
    return insights[0] if insights else None


def build_creative_reasoning(report):
    semantic = _semantic_input(report)
    insights = [
        _focus_insight(semantic), _text_insight(semantic),
        _progression_insight(semantic), _subject_pattern_insight(semantic),
    ]
    insights = [item for item in insights if item]
    timeline = [{
        "time": f"{float(beat['start_time']):.0f}-{float(beat['end_time']):.0f}s",
        "moment": beat["semantic_description"],
        "confidence": beat["confidence"],
    } for beat in semantic.get("beats", [])]
    if not timeline:
        timeline = [{"time": "Opening", "moment": "The available frames are too limited to form a reliable creative beat.", "confidence": "limited"}]
    return {
        "status": "success" if semantic["primary_visual_focus"] != "unavailable" else "limited",
        "opening_snapshot": semantic["opening_clarity_summary"],
        "timeline": timeline,
        "strengths": _strengths(semantic),
        "insights": insights,
        "priority": _priority(insights),
        "experiments": insights[:3],
        "semantic_version": semantic["version"],
        "semantic_confidence": semantic["semantic_confidence"],
    }
