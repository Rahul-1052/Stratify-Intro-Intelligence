"""Conservative pattern aggregation over normalized stored fields only."""

from collections import Counter
from dataclasses import asdict

from core.memory.models import MemorySnapshot

MIN_TENDENCY_ANALYSES = 2
MIN_STABLE_ANALYSES = 4
STABLE_SHARE = 0.70
MIXED_SHARE = 0.60
RECENT_WINDOW = 3
KNOWN_EXPERIMENT_DIMENSIONS = (
    "reveal_timing", "visual_anchor", "information_density",
    "information_order", "structural_rhythm",
)
DIMENSIONS = (
    "opening_strategy", "primary_visual_focus", "progression_style",
    "subject_timing", "subject_presence", "multiple_subjects",
    "written_information_state", "recommendation_state",
)
EXCLUDED = {None, "", "unknown", "unavailable", "uncertain", "not_yet_reviewed", "limited"}


def _pattern(records, dimension):
    values = [getattr(item, dimension, None) for item in records]
    known = [value for value in values if value not in EXCLUDED]
    excluded = len(values) - len(known)
    if not known:
        return {"state": "insufficient_history", "value": None, "observations": 0, "excluded": excluded}
    counts = Counter(known)
    value, count = sorted(counts.items(), key=lambda item: (-item[1], str(item[0])))[0]
    share = count / len(known)
    if len(known) < MIN_TENDENCY_ANALYSES:
        state = "insufficient_history"
    elif len(known) >= MIN_STABLE_ANALYSES and share >= STABLE_SHARE:
        state = "repeated_pattern"
    elif share < MIXED_SHARE:
        state = "mixed_pattern"
    elif records and len(known) >= MIN_TENDENCY_ANALYSES and value in [
        getattr(item, dimension, None) for item in records[-RECENT_WINDOW:]
    ]:
        state = "emerging_pattern" if count == 2 else "occasional_pattern"
    else:
        state = "occasional_pattern"
    return {
        "state": state, "value": value, "observations": len(known), "count": count,
        "distribution": dict(sorted(counts.items(), key=lambda item: str(item[0]))),
        "excluded": excluded,
    }


def aggregate(records, experiments=()):
    records = list(records)
    patterns = {dimension: _pattern(records, dimension) for dimension in DIMENSIONS}
    stable = [f"{key}: {value['value']}" for key, value in patterns.items() if value["state"] == "repeated_pattern"]
    occasional = [f"{key}: {value['value']}" for key, value in patterns.items() if value["state"] == "occasional_pattern"]
    emerging = [f"{key}: {value['value']}" for key, value in patterns.items() if value["state"] == "emerging_pattern"]
    dimensions = {item.dimension for item in experiments}
    contradictions = [key for key, value in patterns.items() if value["state"] == "mixed_pattern"]
    excluded = {key: value["excluded"] for key, value in patterns.items() if value["excluded"]}
    if len(records) < MIN_TENDENCY_ANALYSES:
        confidence = "insufficient_history"
        reasons = ["More saved analyses are needed before a recurring pattern can be supported."]
    elif contradictions:
        confidence = "limited"
        reasons = ["Saved analyses contain mixed patterns.", f"Contradictory dimensions: {', '.join(contradictions)}."]
    elif len(records) >= MIN_STABLE_ANALYSES and stable:
        confidence = "moderate"
        reasons = ["Several analyses repeat the same normalized observations."]
    else:
        confidence = "developing"
        reasons = ["A possible tendency is present, but the saved sample remains small."]
    dates = [item.created_at for item in records if item.created_at]
    snapshot = MemorySnapshot(
        analyses_count=len(records),
        date_range={"start": min(dates), "end": max(dates)} if dates else None,
        patterns=patterns,
        strongest_stable_patterns=stable,
        occasional_patterns=occasional,
        emerging_patterns=emerging,
        unexplored_experiment_dimensions=[item for item in KNOWN_EXPERIMENT_DIMENSIONS if item not in dimensions],
        confidence=confidence,
        confidence_reasons=reasons,
        limitations=["Creator Memory describes repeated structure; it does not contain performance outcomes."],
        diagnostics={"contradictions": contradictions, "excluded_unknown_or_limited": excluded},
    )
    return asdict(snapshot)
