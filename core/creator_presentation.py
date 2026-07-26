"""Deterministic Creator Mode presentation calibration over existing report evidence."""

from dataclasses import asdict, dataclass


CONFIDENCE_ORDER = {"limited": 1, "moderate": 2, "high": 3}
TEXT_DIMENSIONS = {"information_density", "information_order", "text", "written_information"}


def _level(value, fallback="limited"):
    value = str(value or fallback).strip().lower()
    value = {"confirmed": "high", "strong": "high", "medium": "moderate"}.get(value, value)
    return value if value in CONFIDENCE_ORDER else fallback


def _cap(value, maximum):
    return min((_level(value), maximum), key=lambda item: CONFIDENCE_ORDER[item])


def is_text_experiment(item):
    dimension = str(item.get("structural_dimension") or item.get("dimension") or "").lower()
    combined = " ".join(str(item.get(key) or "").lower() for key in (
        "title", "recommendation", "change", "suggested_test",
    ))
    return dimension in TEXT_DIMENSIONS or any(token in combined for token in (
        "written", "text-like", "text overlay", "on-screen text",
    ))


def calibrate_experiments(experiments, text_evidence):
    kept, excluded = [], []
    for item in experiments or []:
        if is_text_experiment(item) and text_evidence not in {"high", "moderate", "confirmed", "strong"}:
            excluded.append({
                "dimension": item.get("structural_dimension") or "text",
                "reason": f"text evidence was {text_evidence or 'unknown'}",
            })
            continue
        kept.append(item)
    return kept[:3], excluded


def creator_confidence_presentation(report, creator):
    confidence = creator.get("confidence_summary") or {}
    validation = creator.get("evidence_validation") or {}
    opportunity = creator.get("biggest_opportunity") or {}
    warnings = list(report.get("warnings") or [])
    pipeline_status = str(report.get("status") or "success").lower()
    text_evidence = _level(confidence.get("text_evidence"))
    structural = _level(confidence.get("evidence_confidence"))
    benchmark_supported = bool(validation.get("benchmark_supported"))
    supported = bool(opportunity.get("supported"))
    contradictions = bool(
        opportunity.get("evidence_consistency") in {"limited", "contradictory", "mixed"}
        or report.get("evidence_contradictions")
    )

    limited_reasons = []
    if warnings:
        limited_reasons.append("some supporting evidence was unavailable")
    if text_evidence == "limited":
        limited_reasons.append("text-like evidence was limited")
    if pipeline_status == "partial":
        analysis_value = "Partial"
        analysis_reason = "Part of the opening was analyzed; some report sections may be unavailable."
    elif pipeline_status == "failed":
        analysis_value = "Failed"
        analysis_reason = "The analysis did not produce a usable report."
    elif limited_reasons:
        analysis_value = "Completed with limited evidence"
        analysis_reason = "The opening was analyzed successfully, though " + " and ".join(limited_reasons) + "."
    else:
        analysis_value = "Completed"
        analysis_reason = "The opening was analyzed successfully."

    if pipeline_status in {"partial", "failed"}:
        coverage = "Limited"
    elif warnings or text_evidence == "limited":
        coverage = "Moderate" if structural in {"high", "moderate"} else "Limited"
    else:
        coverage = {"high": "Strong", "moderate": "Moderate", "limited": "Limited"}[structural]
    coverage_reason = (
        "Visual structure was available, but text-like evidence remained limited."
        if text_evidence == "limited" and structural in {"high", "moderate"}
        else "The report uses the evidence that completed successfully."
        if warnings else "The sampled opening provided consistent structural evidence."
    )

    structural_value = structural.title()
    structural_reason = (
        "Repeated subject and progression patterns support the structural interpretation."
        if structural == "high" else
        "The available structure is readable, with some supporting dimensions limited."
        if structural == "moderate" else
        "The available evidence supports only a cautious structural interpretation."
    )

    downgrade_reasons = []
    raw_recommendation = _level(confidence.get("recommendation_confidence"))
    if not supported:
        recommendation_value = "No supported recommendation"
        recommendation_reason = "The opening was analyzed, but the evidence does not justify a structural change."
    else:
        calibrated = raw_recommendation
        if not benchmark_supported and calibrated == "high":
            calibrated = "moderate"
            downgrade_reasons.append("no qualified benchmark comparison was available")
        if contradictions:
            calibrated = _cap(calibrated, "limited")
            downgrade_reasons.append("supporting evidence contained contradictions")
        if is_text_experiment(opportunity) and text_evidence == "limited":
            calibrated = _cap(calibrated, "limited")
            downgrade_reasons.append("the recommendation depends partly on uncertain text-like evidence")
        recommendation_value = calibrated.title()
        if downgrade_reasons:
            recommendation_reason = (
                f"The recommendation is {str(opportunity.get('source') or 'observation-backed').lower()}, but "
                + " and ".join(downgrade_reasons) + "."
            )
        elif benchmark_supported:
            recommendation_reason = "Qualified comparison evidence supports this controlled test."
        else:
            recommendation_reason = "The recommendation is supported by repeated observations in this opening."

    return {
        "analysis_status": {"value": analysis_value, "explanation": analysis_reason},
        "evidence_coverage": {"value": coverage, "explanation": coverage_reason},
        "structural_confidence": {"value": structural_value, "explanation": structural_reason},
        "recommendation_confidence": {
            "value": recommendation_value, "explanation": recommendation_reason,
        },
        "diagnostics": {
            "pipeline_status": pipeline_status,
            "raw_structural_confidence": structural,
            "raw_recommendation_confidence": raw_recommendation,
            "benchmark_supported": benchmark_supported,
            "text_evidence": text_evidence,
            "contradictions": contradictions,
            "recommendation_downgrade_reasons": downgrade_reasons,
            "limited_status_reasons": limited_reasons,
        },
    }


def creator_status_message(presentation, supported_recommendation=True):
    if not supported_recommendation:
        return "The opening was analyzed, but the evidence does not justify recommending a structural change."
    return presentation["analysis_status"]["explanation"]
