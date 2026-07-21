"""Deterministic opportunity reasoning over Creative Understanding and Structure."""

from core.observers.semantic_observer import observe_semantics
from core.understanding import (
    CreativeStructure,
    CreativeUnderstanding,
    build_creative_understanding,
    understand_creative_opening,
)


CONFIDENCE_WEIGHT = {"high": 3, "moderate": 2, "limited": 1}
IMPORTANCE_WEIGHT = {"high": 3, "moderate": 2, "limited": 1}


def _semantic_input(report):
    semantic = report.get("semantic_observation") or {}
    if semantic.get("version") == "observation-semantics-v2":
        return semantic
    return observe_semantics((report.get("vision") or {}).get("frame_observations") or [])


def _reasoning_inputs(report):
    """Isolated compatibility path for reports produced before Sprint A."""
    semantic = _semantic_input(report)
    structure_value = report.get("creative_structure")
    understanding_value = report.get("creative_understanding")
    compatibility_mode = not bool(structure_value and understanding_value)
    if structure_value:
        structure = CreativeStructure.from_dict(structure_value)
    else:
        structure, _ = understand_creative_opening(semantic)
    if understanding_value:
        understanding = CreativeUnderstanding.from_dict(understanding_value)
    else:
        understanding = build_creative_understanding(structure, semantic)
    return semantic, structure, understanding, compatibility_mode


def _semantic_evidence(semantic, *fields):
    evidence = []
    direct = semantic.get("supporting_evidence", []) or []
    for field in fields:
        value = semantic.get(field, "unavailable")
        if value not in {None, "", "unavailable"}:
            evidence.append({"semantic_field": field, "observed_value": value})
    if direct:
        evidence.append({"semantic_field": "supporting_frames", "observed_value": len(direct)})
    return evidence


def _candidate(
    dimension, title, current, alternative, rationale, recommendation, constant,
    comparison, evidence, confidence, importance="moderate", limitations=None,
):
    evidence = list(evidence or [])
    if not evidence or current == "unavailable" or alternative == "unavailable":
        return None
    consistency = "consistent" if len(evidence) >= 2 else "limited"
    limitations = list(limitations or [])
    if confidence == "limited":
        limitations.append("The underlying structural evidence has limited confidence.")
    return {
        "opportunity_type": dimension,
        "structural_dimension": dimension,
        "current_structure": current,
        "alternative_structure": alternative,
        "rationale": rationale,
        "supporting_evidence": evidence,
        "evidence_count": len(evidence),
        "evidence_consistency": consistency,
        "structural_importance": importance,
        "confidence": confidence,
        "limitations": limitations,
        "title": title,
        "observation": f"The opening currently uses {current}.",
        "interpretation": rationale,
        "recommendation": recommendation,
        "reason": f"This controlled alternative tests {alternative} without assuming it will perform better.",
        "what_stays_constant": constant,
        "how_to_compare": comparison,
        "source": "Observation-backed",
        "evidence_key": ";".join(
            f"{item['semantic_field']}:{item['observed_value']}"
            for item in evidence if item["semantic_field"] != "supporting_frames"
        ),
        "benchmark_supported": False,
    }


def _opportunity_candidates(structure, understanding, semantic):
    candidates = []
    confidence = understanding.confidence
    direct_count = len(semantic.get("supporting_evidence", []) or [])
    if direct_count < 2:
        return []

    if structure.reveal_pattern in {"anchor develops early", "anchor revealed later"}:
        candidates.append(_candidate(
            "reveal_timing", "Establish the visual priority sooner", structure.reveal_pattern,
            "the same visual anchor established in the first phase",
            f"{understanding.summary} The visual anchor is established after the opening begins.",
            "Move the earliest existing frame with the established anchor to the first phase.",
            "Keep the footage, audio, written message, duration, and later sequence unchanged.",
            "Compare which version establishes the same visual anchor earlier without losing necessary context.",
            _semantic_evidence(semantic, "focus_clarity", "primary_visual_focus"), confidence, "high",
        ))
    if structure.visual_anchor in {"multiple subjects", "alternating subjects", "mixed elements"} or structure.reveal_pattern == "multiple anchors remain in play":
        candidates.append(_candidate(
            "visual_anchor", "Give the first phase one visual anchor", structure.visual_anchor,
            "one established anchor before the existing multi-element sequence",
            f"{understanding.summary} More than one element carries structural emphasis at the start.",
            "Create an alternate first phase that holds the intended primary anchor before the existing sequence.",
            "Keep the source footage, audio, duration, color, and later sequence unchanged.",
            "Compare which version produces more consistent descriptions of the opening's primary focus.",
            _semantic_evidence(semantic, "primary_visual_focus", "focus_clarity"), confidence, "high",
        ))
    if structure.information_density in {"continuously layered", "written-information dense"}:
        candidates.append(_candidate(
            "information_density", "Separate the first visual and written beats", structure.information_density,
            "a visual-first phase followed by the same written information",
            f"{understanding.summary} Written and visual information remain layered through most of the sample.",
            "Delay the existing written cue until the next semantic phase.",
            "Keep the wording, typography, footage, audio, and total duration unchanged.",
            "Compare whether each version makes the visual anchor and written message separately identifiable.",
            _semantic_evidence(semantic, "text_role", "information_mode"), confidence, "moderate",
        ))
    elif structure.information_density == "layered at selected moments":
        candidates.append(_candidate(
            "information_order", "Test the handoff from image to written context", structure.information_order,
            "the same image and written context introduced in separate phases",
            f"{understanding.summary} The written cue creates a distinct information handoff within the opening.",
            "Move the existing written cue to the next semantic phase in an alternate cut.",
            "Keep the wording, position, footage, audio, visual anchor, and total duration unchanged.",
            "Compare whether separating the image and written cue makes their sequence clearer while preserving the message.",
            _semantic_evidence(semantic, "text_role", "information_mode"), confidence, "moderate",
            limitations=["The evidence identifies a timing alternative, not a proven weakness."],
        ))
    if structure.attention_evolution == "moves through frequent purpose changes":
        candidates.append(_candidate(
            "structural_rhythm", "Let one opening phase carry more weight", structure.structural_rhythm,
            "fewer phases with the clearest existing phase held longer",
            f"{understanding.summary} Several purpose changes occur within the sampled opening.",
            "Remove one early phase and extend the clearest remaining phase by the same duration.",
            "Keep the audio, endpoint, main anchor, message, and total duration unchanged.",
            "Compare which version is easier to recount after one silent viewing.",
            _semantic_evidence(semantic, "visual_progression"), confidence, "moderate",
        ))
    if structure.opening_strategy == "text-first" and structure.visual_anchor in {"unavailable", "written information", "mixed elements"}:
        candidates.append(_candidate(
            "information_order", "Test visual context before written context", structure.information_order,
            "visual information followed by the same written context",
            f"{understanding.summary} Written information arrives before a stable non-text visual anchor is established.",
            "Create an alternate order that introduces the clearest existing visual phase before the written cue.",
            "Keep the wording, footage, audio, duration, and endpoint unchanged.",
            "Compare which order communicates the same opening idea with fewer competing priorities.",
            _semantic_evidence(semantic, "opening_mode", "information_mode", "primary_visual_focus"), confidence, "high",
        ))
    return [item for item in candidates if item]


def _rank_candidates(candidates):
    ranked = []
    for candidate in candidates:
        contradictions = 1 if candidate["evidence_consistency"] != "consistent" else 0
        missing = sum(value in {None, "", "unavailable"} for value in (
            candidate["current_structure"], candidate["alternative_structure"]
        ))
        benchmark = 2 if candidate.get("benchmark_supported") else 0
        score = (
            min(candidate["evidence_count"], 4) +
            IMPORTANCE_WEIGHT.get(candidate["structural_importance"], 0) +
            CONFIDENCE_WEIGHT.get(candidate["confidence"], 0) + benchmark -
            contradictions * 2 - missing * 3
        )
        ranked.append({**candidate, "ranking": {
            "score": score, "evidence_count": candidate["evidence_count"],
            "evidence_consistency": candidate["evidence_consistency"],
            "benchmark_support": bool(candidate.get("benchmark_supported")),
            "structural_importance": candidate["structural_importance"],
            "confidence": candidate["confidence"], "contradiction_penalty": contradictions * 2,
            "missing_evidence_penalty": missing * 3,
        }})
    return sorted(ranked, key=lambda item: (-item["ranking"]["score"], item["structural_dimension"]))


def _diverse_experiments(ranked):
    experiments, dimensions = [], set()
    for candidate in ranked:
        dimension = candidate["structural_dimension"]
        if dimension in dimensions:
            continue
        dimensions.add(dimension)
        experiments.append(candidate)
        if len(experiments) == 3:
            break
    return experiments


def _strengths(structure, understanding, semantic):
    if len(semantic.get("supporting_evidence", []) or []) < 2:
        return []
    strengths = []
    if structure.reveal_pattern == "anchor established immediately" and structure.visual_anchor != "unavailable":
        strengths.append({"title": "The opening establishes a clear visual anchor immediately", "explanation": f"The {structure.visual_anchor} leads from the first phase, preserving a readable hierarchy."})
    if structure.structural_consistency == "repeated purpose":
        strengths.append({"title": "The opening maintains one structural purpose", "explanation": "The edit changes presentation while preserving the same opening function across its phases."})
    if structure.opening_strategy == "context-first" and structure.reveal_pattern in {"anchor established immediately", "anchor develops early"}:
        strengths.append({"title": "The information sequence progresses from context to anchor", "explanation": "The setting is established before the more specific visual anchor takes priority."})
    if structure.information_density == "layered at selected moments":
        strengths.append({"title": "Written context has a defined structural role", "explanation": "Written information appears in selected phases instead of competing with the imagery throughout the opening."})
    return strengths


def build_creative_reasoning(report):
    semantic, structure, understanding, compatibility_mode = _reasoning_inputs(report)
    ranked = _rank_candidates(_opportunity_candidates(structure, understanding, semantic))
    beat_references = [
        {"beat_index": index, "beat_purpose": beat.get("beat_purpose", "unavailable")}
        for index, beat in enumerate(semantic.get("beats", []))
    ]
    ranked = [{**candidate, "beat_references": beat_references} for candidate in ranked]
    experiments = _diverse_experiments(ranked)
    timeline = [{
        "time": f"{float(beat['start_time']):.0f}-{float(beat['end_time']):.0f}s",
        "moment": beat["semantic_description"], "confidence": beat["confidence"],
    } for beat in semantic.get("beats", [])]
    if not timeline:
        timeline = [{"time": "Opening", "moment": "The available frames are too limited to form a reliable creative beat.", "confidence": "limited"}]
    trace = {
        "semantic_evidence": understanding.supporting_evidence,
        "creative_structure": structure.to_dict(),
        "creative_understanding": understanding.to_dict(),
        "opportunity_candidates": ranked,
        "selected_opportunity": ranked[0] if ranked else None,
        "experiments": experiments,
        "compatibility_mode": compatibility_mode,
    }
    return {
        "status": "success" if structure.opening_strategy != "unavailable" else "limited",
        "opening_snapshot": understanding.summary,
        "timeline": timeline,
        "strengths": _strengths(structure, understanding, semantic),
        "insights": ranked,
        "opportunity_candidates": ranked,
        "priority": ranked[0] if ranked else None,
        "experiments": experiments,
        "semantic_version": semantic.get("version", "unavailable"),
        "semantic_confidence": semantic.get("semantic_confidence", "limited"),
        "creative_structure": structure.to_dict(),
        "creative_understanding": understanding.to_dict(),
        "traceability": trace,
    }
