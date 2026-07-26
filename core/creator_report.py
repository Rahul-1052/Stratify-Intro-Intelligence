"""Compose the Creator report from Creative Reasoning and optional validation."""

from core.reasoning.creative_reasoning import build_creative_reasoning
from core.product_access import access_for_mode
from core.creator_presentation import calibrate_experiments


def _creator_text(text, text_confidence):
    value = str(text or "").strip()
    if text_confidence != "limited":
        return value
    replacements = {
        "without written information": "without confirmed written information",
        "Written cues": "Possible written information",
        "Written information": "Possible written information",
        "written cues": "possible written information",
        "written information": "possible written information",
        "on-screen text": "text-like visual elements",
    }
    for source, replacement in replacements.items():
        value = value.replace(source, replacement)
    return (value
            .replace("without confirmed possible written information", "without confirmed written information")
            .replace("possible possible written information", "possible written information")
            .replace("the possible written information is established", "text-like visual elements are present"))


def _limitation(item, fallback):
    limitations = item.get("limitations") or []
    return str(limitations[0]) if limitations else fallback


def _text_confidence(report, semantic, fallback):
    explicit = semantic.get("text_evidence_confidence")
    if explicit:
        return explicit
    frames = ((report.get("vision") or {}).get("frame_observations") or [])
    observed = [str(frame.get("text_overlay_confidence", "")).lower()
                for frame in frames if frame.get("text_overlay") is True]
    return "limited" if "limited" in observed else fallback


def _creator_experiment(item):
    current = str(item.get("current_structure") or "the current opening structure")
    change = str(item.get("recommendation") or item.get("suggested_test") or item.get("experiment") or "")
    reason = str(item.get("reason") or item.get("why_it_matters") or item.get("why") or "")
    return {
        **item,
        "hypothesis": reason,
        "change": change,
        "version_a": f"Keep {current}.",
        "version_b": change,
        "support": str(
            item.get("observation")
            or (
                f"Repeated evidence supports testing the {str(item.get('structural_dimension') or 'opening structure').replace('_', ' ')}."
            )
        ),
        "limitation": _limitation(item, "This is a controlled creative test, not a predicted performance result."),
    }


def _benchmark_experiment(item):
    title = str(item.get("title") or "").strip()
    change = str(item.get("suggested_test") or item.get("experiment") or "").strip()
    reason = str(item.get("why_it_matters") or item.get("why") or "").strip()
    if not title or not change or not reason:
        return None
    return {
        "title": title,
        "observation": "A qualified comparison set showed a repeatable creative difference for this opening decision.",
        "interpretation": "That contrast makes this a reasonable direction to test, not a guaranteed performance outcome.",
        "recommendation": change,
        "reason": reason,
        "what_stays_constant": "Keep every other opening decision and the total intro duration unchanged.",
        "how_to_compare": "Compare the two versions for clarity of the intended opening idea before reviewing performance data.",
        "source": "Benchmark-supported",
        "evidence_key": "qualified_benchmark_comparison",
        "benchmark_supported": True,
        "structural_dimension": str(item.get("structural_dimension") or "benchmark_comparison"),
        "confidence": str(item.get("confidence") or "moderate"),
        "limitations": ["Benchmark support is directional and does not guarantee an outcome."],
    }


def build_creator_report(report, creative_reasoning=None, product_mode="creator"):
    creative = creative_reasoning or build_creative_reasoning(report)
    benchmark = report.get("benchmark") or {}
    quality = benchmark.get("benchmark_quality") or {}
    patterns = report.get("patterns") or {}
    experiments = list(creative.get("experiments") or [])

    if quality.get("eligible_for_directional_learning"):
        benchmark_items = patterns.get("top_creator_experiments") or patterns.get("recommendations") or []
        for item in benchmark_items:
            enriched = _benchmark_experiment(item)
            existing_dimensions = {existing.get("structural_dimension") for existing in experiments}
            if enriched and enriched["title"] not in {existing.get("title") for existing in experiments} and enriched["structural_dimension"] not in existing_dimensions:
                experiments.insert(0, enriched)
            if len(experiments) >= 3:
                break

    experiments = [_creator_experiment(item) for item in experiments[:3]]
    semantic = report.get("semantic_observation") or {}
    text_confidence = _text_confidence(report, semantic, creative.get("semantic_confidence", "limited"))
    experiments, excluded_text_experiments = calibrate_experiments(experiments, text_confidence)
    priority = experiments[0] if experiments else None
    analysis_status = report.get("status", "success")
    evidence_confidence = creative.get("semantic_confidence", "limited")
    if priority:
        opportunity = {
            "title": priority["title"],
            "summary": str(priority.get("observation") or f"The opening currently uses {priority.get('current_structure', 'the observed structure')}."),
            "why_test": priority["reason"],
            "current_structure": priority.get("current_structure", "Current observed structure"),
            "proposed_alternative": priority.get("alternative_structure") or priority.get("recommendation", ""),
            "keep_constant": priority.get("what_stays_constant", "Keep the remaining opening decisions unchanged."),
            "confidence": priority.get("confidence", "limited"),
            "limitation": _limitation(priority, "No qualified benchmark support is available."),
            "source": priority.get("source", "Observation-backed"),
            "structural_dimension": priority.get("structural_dimension"),
            "evidence_consistency": priority.get("evidence_consistency"),
            "supported": True,
        }
    else:
        if creative.get("status") == "limited":
            opportunity = {
                "title": "No supported structural change yet",
                "summary": "The opening was processed, but the available visual evidence is not specific enough to recommend an edit without guessing.",
                "why_test": "Upload a clearer opening clip or keep the current structure until stronger evidence is available.",
            }
        else:
            opportunity = {
                "title": "No supported structural change yet",
                "summary": "The opening is structurally readable, but the current evidence does not support one alternative strongly enough to prioritize it.",
                "why_test": "Keep the current structure until direct or qualified comparison evidence supports a controlled alternative.",
            }
        opportunity.update({
            "current_structure": "The current opening",
            "proposed_alternative": "No controlled alternative is justified yet",
            "keep_constant": "Keep the current edit unchanged.",
            "confidence": "limited",
            "limitation": "The evidence does not justify a recommendation.",
            "supported": False,
        })

    strengths = creative["strengths"]
    strength_state = "supported" if strengths else "neutral"
    benchmark_supported = bool(quality.get("eligible_for_directional_learning"))
    recommendation_confidence = opportunity.get("confidence", "limited") if opportunity.get("supported") else "limited"

    return {
        "report_version": "creator-product-v1",
        "opening_snapshot": {"summary": _creator_text(creative["opening_snapshot"], text_confidence)},
        "intro_timeline": creative["timeline"],
        "whats_working": strengths,
        "strength_state": strength_state,
        "biggest_opportunity": opportunity,
        "experiments": experiments,
        "creative_reasoning_status": creative.get("status", "limited"),
        "evidence_validation": {
            "status": "validated" if benchmark_supported else "observation_only",
            "label": "Qualified comparison evidence supports part of this report." if benchmark_supported else "This report uses the opening itself; no qualified comparison set was available.",
            "benchmark_supported": benchmark_supported,
            "benchmark_quality": quality,
        },
        "confidence_summary": {
            "analysis_completeness": "partial" if analysis_status == "partial" else "complete" if analysis_status == "success" else "limited",
            "evidence_confidence": evidence_confidence,
            "recommendation_confidence": recommendation_confidence,
            "text_evidence": text_confidence,
            "plain_language": (
                "Visual structure is available, but text-like visual evidence is limited."
                if text_confidence == "limited" else
                "The report is grounded in repeated visual evidence from the sampled opening."
            ),
        },
        "additional_observations": creative["timeline"],
        "product_access": access_for_mode(product_mode).to_dict(),
        "presentation_diagnostics": {
            "excluded_text_experiments": excluded_text_experiments,
            "section_summary_sources": {
                "opening_snapshot": "creative_understanding.summary",
                "biggest_opportunity": "selected_opportunity.observation",
                "experiment_support": "selected_experiment.observation",
            },
        },
    }
