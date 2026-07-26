"""Compare a current normalized analysis with previous saved history."""

from types import SimpleNamespace

from core.memory.aggregator import DIMENSIONS, EXCLUDED, aggregate


def compare_current(current, previous):
    previous = list(previous)
    if not previous:
        return {"state": "insufficient_history", "message": "There is not enough saved history yet to compare this opening reliably.", "evidence": {}}
    current = current if hasattr(current, "opening_strategy") else SimpleNamespace(**current)
    baseline = aggregate(previous)
    comparable, matches, differs, new = [], [], [], []
    for dimension in DIMENSIONS:
        value = getattr(current, dimension, None)
        if value in EXCLUDED:
            continue
        pattern = baseline["patterns"][dimension]
        if not pattern.get("observations"):
            new.append(dimension)
            continue
        comparable.append(dimension)
        if value == pattern.get("value"):
            matches.append(dimension)
        else:
            differs.append(dimension)
            if value not in pattern.get("distribution", {}):
                new.append(dimension)
    evidence = {"matches": matches, "differs": differs, "new": new, "baseline_analyses": len(previous)}
    if not comparable and not new:
        return {"state": "evidence_too_limited", "message": "The available evidence is too limited for a historical comparison.", "evidence": evidence}
    if len(previous) < 2:
        return {"state": "insufficient_history", "message": "One saved analysis provides context, but more history is needed for a reliable comparison.", "evidence": evidence}
    if new:
        return {"state": "newly_observed_pattern", "message": f"This opening introduces a newly observed {new[0].replace('_', ' ')} pattern.", "evidence": evidence}
    if matches and not differs:
        return {"state": "matches_typical_pattern", "message": "This opening follows the patterns repeated across your saved analyses.", "evidence": evidence}
    if matches and differs:
        return {"state": "partially_matches_history", "message": "Some opening choices are familiar, while others differ from your recent history.", "evidence": evidence}
    return {"state": "differs_from_usual_pattern", "message": "This opening differs from most of the patterns in your saved history.", "evidence": evidence}
