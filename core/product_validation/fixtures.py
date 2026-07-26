"""Deterministic validation-system fixtures; never real-video claims."""

from copy import deepcopy


def _base(case_id, niche):
    return {
        "case_id": case_id, "source": f"fixture://{case_id}", "niche": niche,
        "source_type": "fixture", "enabled": True, "validation_kind": "fixture UI validation",
        "report": {"status": "success", "video": {"title": f"Fixture {case_id}"},
          "creator_report": {
            "opening_snapshot": {"summary": "One subject appears immediately and remains the visual anchor."},
            "creative_understanding": {"summary": "The opening establishes one clear visual purpose."},
            "biggest_opportunity": {"title": "Hold the first visual priority", "summary": "A second element arrives during the opening.", "supported": True, "confidence": "moderate"},
            "experiments": [{"title": "Delay the second element", "change": "Hold the first subject alone for one additional beat.", "confidence": "moderate", "source": "observation-backed"}],
            "confidence_summary": {"structural_confidence": "high", "recommendation_confidence": "moderate", "text_evidence": "confirmed"},
            "limitations": ["Fixture evidence does not represent a creator result."]
          }}
    }


def fixture_cases():
    cases = []
    for case_id, niche in (("strong-visual", "technology"), ("limited-text", "education"),
                           ("no-benchmark", "food"), ("one-experiment", "gaming"),
                           ("multiple-experiments", "vlog"), ("no-opportunity", "podcast"),
                           ("abstention", "documentary"), ("contradictory", "finance"),
                           ("saved-history", "entertainment"), ("memory-comparison", "small creator"),
                           ("partial-history", "small creator")):
        item = _base(case_id, niche)
        cases.append(item)
    cases[1]["report"]["creator_report"]["confidence_summary"]["text_evidence"] = "limited"
    cases[2]["report"]["benchmark_intelligence"] = {"status": "unavailable"}
    cases[4]["report"]["creator_report"]["experiments"].append({
        "title": "Reverse the existing two beats", "change": "Swap only their order.",
        "confidence": "moderate", "source": "observation-backed"})
    for index in (5, 6):
        cases[index]["report"]["creator_report"]["biggest_opportunity"]["supported"] = False
        cases[index]["report"]["creator_report"]["experiments"] = []
    cases[6]["report"]["creator_report"]["biggest_opportunity"]["title"] = "No supported recommendation"
    cases[7]["report"]["creator_report"]["confidence_summary"]["evidence_consistency"] = "contradictory"
    cases[8]["report"]["saved_history"] = {"revision": 2, "analysis_date": "2026-01-01T00:00:00Z"}
    cases[9]["report"]["creator_memory_comparison"] = {"state": "partially_matches_history"}
    cases[10]["report"] = {"status": "partial", "normalized_summary": {"opening": "Historical fixture"}, "saved_history": {"revision": 1}}
    return cases
