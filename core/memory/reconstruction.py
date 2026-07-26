"""Compatibility adapter from saved memory records to the Creator report contract."""

from core.memory.models import AnalysisRecord


def reconstruct_creator_report(record, video=None, revision=1):
    video = video or {}
    diagnostics = {"analysis_id": getattr(record, "id", None), "missing_fields": []}
    if not isinstance(record, AnalysisRecord):
        return {
            "status": "fallback",
            "message": "This saved analysis could not be reconstructed.",
            "unavailable_details": ["The saved analysis payload is not readable."],
            "diagnostics": {**diagnostics, "reason": "invalid_record_type"},
        }

    snapshot = record.snapshot if isinstance(record.snapshot, dict) else {}
    confidence = record.confidence_summary if isinstance(record.confidence_summary, dict) else {}
    opportunity = record.opportunity if isinstance(record.opportunity, dict) else {}
    experiments = record.experiments if isinstance(record.experiments, list) else []
    reasoning = record.reasoning_summary if isinstance(record.reasoning_summary, dict) else {}
    if not str(snapshot.get("summary") or "").strip():
        diagnostics["missing_fields"].append("opening_snapshot.summary")
    if not confidence:
        diagnostics["missing_fields"].append("confidence_summary")
    historical = {
        "analysis_id": record.id, "analysis_date": record.created_at,
        "analysis_version": record.analysis_version, "revision": revision,
        "title": video.get("title"),
    }
    if diagnostics["missing_fields"]:
        return {
            "status": "fallback",
            "message": "This older saved analysis contains only a partial historical record.",
            "normalized_summary": {
                "opening_strategy": record.opening_strategy,
                "primary_visual_focus": record.primary_visual_focus,
                "progression_style": record.progression_style,
                "recommendation_state": record.recommendation_state,
                "analysis_completeness": record.analysis_completeness,
                "limitations": list(record.evidence_limitations or []),
            },
            "unavailable_details": [
                "The full opening narrative or confidence details were not stored for this revision."
            ],
            "diagnostics": diagnostics,
            "historical": historical,
        }

    text_state = record.written_information_state
    confidence = dict(confidence)
    confidence.setdefault("analysis_completeness", record.analysis_completeness or "limited")
    confidence.setdefault("evidence_confidence", "limited")
    confidence.setdefault("recommendation_confidence", record.recommendation_confidence or "limited")
    if text_state == "limited":
        confidence["text_evidence"] = "limited"
    else:
        confidence.setdefault("text_evidence", "unavailable")
    confidence.setdefault(
        "plain_language",
        "Written-information evidence remains limited in this saved analysis."
        if text_state == "limited"
        else "This historical report preserves the evidence confidence recorded at analysis time.",
    )
    opportunity = dict(opportunity)
    opportunity.setdefault("supported", record.recommendation_state == "supported")
    opportunity.setdefault("title", "No supported structural change yet")
    opportunity.setdefault("summary", "The saved evidence did not support a structural change.")
    opportunity.setdefault("current_structure", "The saved opening structure")
    opportunity.setdefault("proposed_alternative", "No controlled alternative was stored")
    opportunity.setdefault("why_test", "No additional claim is made from historical memory.")
    opportunity.setdefault("confidence", record.recommendation_confidence or "limited")
    opportunity.setdefault(
        "limitation",
        (record.evidence_limitations or ["No additional historical limitation was stored."])[0],
    )
    creator_report = {
        "report_version": record.analysis_version,
        "opening_snapshot": snapshot,
        "intro_timeline": reasoning.get("additional_observations") or [],
        "whats_working": [],
        "strength_state": "neutral",
        "biggest_opportunity": opportunity,
        "experiments": experiments[:3],
        "creative_reasoning_status": reasoning.get("status") or "limited",
        "evidence_validation": {
            "status": "historical_record",
            "label": "This is a saved historical analysis; no new acquisition or analysis was run.",
            "benchmark_supported": False,
            "benchmark_quality": {},
        },
        "confidence_summary": confidence,
        "additional_observations": reasoning.get("additional_observations") or [],
    }
    report = {
        "status": "partial" if record.analysis_completeness in {"partial", "limited"} else "success",
        "video": {"title": video.get("title") or "Saved video project"},
        "creator_report": creator_report,
        "creative_structure": record.creative_structure,
        "creative_understanding": record.creative_understanding,
        "warnings": list(record.evidence_limitations or []),
        "saved_history": historical,
    }
    diagnostics.update({
        "status": "reconstructed", "experiments_count": len(experiments),
        "limited_text_preserved": text_state == "limited",
        "abstention_preserved": not opportunity.get("supported"),
        "analysis_pipeline_rerun": False,
    })
    return {"status": "reconstructed", "report": report, "diagnostics": diagnostics}
