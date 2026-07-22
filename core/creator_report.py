"""Compose the Creator report from Creative Reasoning and optional validation."""

from core.reasoning.creative_reasoning import build_creative_reasoning


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


def build_creator_report(report, creative_reasoning=None):
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

    priority = experiments[0] if experiments else creative.get("priority")
    if priority:
        opportunity = {
            "title": priority["title"],
            "summary": priority["interpretation"],
            "why_test": priority["reason"],
        }
    else:
        if creative.get("status") == "limited":
            opportunity = {
                "title": "Gather a clearer opening sample",
                "summary": "The available evidence is not specific enough to choose an editing priority without guessing.",
                "why_test": "A readable opening clip is required before Stratify can recommend a defensible creative change.",
            }
        else:
            opportunity = {
                "title": "No supported structural change yet",
                "summary": "The opening is structurally readable, but the current evidence does not support one alternative strongly enough to prioritize it.",
                "why_test": "Keep the current structure until direct or qualified comparison evidence supports a controlled alternative.",
            }

    return {
        "opening_snapshot": {"summary": creative["opening_snapshot"]},
        "intro_timeline": creative["timeline"],
        "whats_working": creative["strengths"],
        "biggest_opportunity": opportunity,
        "experiments": experiments[:3],
        "creative_reasoning_status": creative.get("status", "limited"),
        "evidence_validation": {
            "status": "validated" if quality.get("eligible_for_directional_learning") else "observation_only",
            "label": "Benchmark-enriched" if quality.get("eligible_for_directional_learning") else "Creator guidance comes from the intro itself; benchmark validation was unavailable.",
            "benchmark_supported": bool(quality.get("eligible_for_directional_learning")),
            "benchmark_quality": quality,
        },
    }
