"""Explainable evaluation agreement, aggregate metrics, and failure analysis."""

from collections import Counter, defaultdict

from core.evaluation.evaluation_models import FieldAgreement


SEMANTIC_FIELDS = (
    "focus_clarity", "text_role", "primary_visual_focus", "opening_mode",
    "visual_progression",
)
CONFIDENCE_VALUES = {"high": 1.0, "moderate": 0.6, "limited": 0.3, "unavailable": 0.0}
PARTIAL_NEIGHBORS = {
    "focus_clarity": {frozenset(("immediate", "develops_early")), frozenset(("develops_early", "delayed"))},
    "visual_progression": {frozenset(("mostly_held", "gradual_change")), frozenset(("gradual_change", "distinct_beats")), frozenset(("distinct_beats", "frequent_change"))},
    "primary_visual_focus": {frozenset(("person", "one_subject_dominant")), frozenset(("multiple_people", "alternating_subjects"))},
}


def _normalize(value):
    return str(value).strip().lower().replace(" ", "_") if value is not None else None


def _creator_prediction(field, report):
    creator = report.get("creator_report", {}) or {}
    if field == "best_strength":
        values = creator.get("whats_working", []) or []
        return (values[0].get("title") if values and isinstance(values[0], dict) else values[0]) if values else None
    if field == "largest_weakness":
        return (creator.get("biggest_opportunity") or {}).get("title")
    if field == "expected_experiment":
        values = creator.get("experiments", []) or []
        return (values[0].get("title") if values else None)
    return None


def compare_manual_labels(manual, report):
    semantic = report.get("semantic_observation", {}) or {}
    comparisons = []
    for field, expected in (manual or {}).items():
        if expected is None or field in {"manual_confidence", "reviewer_notes"}:
            continue
        if field == "number_of_semantic_beats":
            predicted = len(semantic.get("beats", []) or [])
            difference = predicted - int(expected)
            result = "correct" if difference == 0 else "partial" if abs(difference) == 1 else "incorrect"
            explanation = f"Predicted {predicted} beats; expected {expected}; difference {difference:+d}."
        else:
            predicted = semantic.get(field) if field in SEMANTIC_FIELDS else _creator_prediction(field, report)
            left, right = _normalize(expected), _normalize(predicted)
            if left == right and left is not None:
                result, explanation = "correct", "Predicted value matches the manual label."
            elif frozenset((left, right)) in PARTIAL_NEIGHBORS.get(field, set()):
                result, explanation = "partial", "Prediction is an adjacent calibrated classification."
            elif field in {"best_strength", "largest_weakness", "expected_experiment"} and left and right:
                expected_terms, predicted_terms = set(left.split("_")), set(right.split("_"))
                overlap = expected_terms & predicted_terms
                result = "partial" if overlap else "incorrect"
                explanation = "Text labels share a concrete concept." if overlap else "Text labels describe different concepts."
            else:
                result, explanation = "incorrect", "Predicted value differs from the manual label."
        comparisons.append(FieldAgreement(field, expected, predicted, result, explanation))
    return comparisons


def _rate(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator, "rate": round(numerator / denominator, 4) if denominator else None}


def calculate_metrics(results):
    results = list(results or [])
    semantics = [(item.report.get("semantic_observation", {}) or {}) for item in results]
    reports = [item.report for item in results]
    semantic_total = len(SEMANTIC_FIELDS) * len(semantics)
    available = sum(semantic.get(field) not in {None, "", "unavailable"} for semantic in semantics for field in SEMANTIC_FIELDS)
    raw_coverage = sum(bool((report.get("vision") or {}).get("frame_observations")) for report in reports)
    confidence_values = [CONFIDENCE_VALUES.get(str(item.get("semantic_confidence", "unavailable")).lower(), 0.0) for item in semantics]
    creator_confidences = []
    for report in reports:
        experiments = ((report.get("creator_report") or {}).get("experiments") or [])
        values = [CONFIDENCE_VALUES.get(str(item.get("confidence", "unavailable")).lower(), 0.0) for item in experiments]
        if values:
            creator_confidences.append(sum(values) / len(values))
    agreements = [agreement for item in results for agreement in item.agreements]
    correct = sum(item.result == "correct" for item in agreements)
    partial = sum(item.result == "partial" for item in agreements)
    categories = defaultdict(list)
    for item in results:
        categories[item.category].extend(item.agreements)
    benchmark_success = sum(bool(((report.get("creator_report") or {}).get("evidence_validation") or {}).get("benchmark_supported")) for report in reports)
    return {
        "video_count": len(results),
        "observation_coverage": _rate(raw_coverage, len(results)),
        "semantic_coverage": _rate(available, semantic_total),
        "unavailable_field_rate": _rate(semantic_total - available, semantic_total),
        "average_semantic_confidence": round(sum(confidence_values) / len(confidence_values), 3) if confidence_values else None,
        "average_creator_confidence": round(sum(creator_confidences) / len(creator_confidences), 3) if creator_confidences else None,
        "recommendation_count": sum(bool((report.get("creator_report") or {}).get("biggest_opportunity")) for report in reports),
        "experiment_count": sum(len((report.get("creator_report") or {}).get("experiments", []) or []) for report in reports),
        "average_beat_count": round(sum(len(item.get("beats", []) or []) for item in semantics) / len(semantics), 2) if semantics else None,
        "average_report_generation_seconds": round(sum(item.generation_seconds for item in results) / len(results), 3) if results else None,
        "benchmark_success_rate": _rate(benchmark_success, len(results)),
        "benchmark_failure_rate": _rate(len(results) - benchmark_success, len(results)),
        "observation_only_rate": _rate(len(results) - benchmark_success, len(results)),
        "manual_agreement_rate": _rate(correct, len(agreements)),
        "manual_partial_rate": _rate(partial, len(agreements)),
        "per_category_agreement": {category: _rate(sum(x.result == "correct" for x in values), len(values)) for category, values in sorted(categories.items())},
    }


def analyze_failures(results):
    results = list(results or [])
    wrong_fields = Counter()
    unavailable = Counter()
    benchmark_failures = Counter()
    category_failures = Counter()
    recommendations = Counter()
    experiments = Counter()
    empty_sections = Counter()
    confidence_by_field = defaultdict(list)
    for item in results:
        semantic = item.report.get("semantic_observation", {}) or {}
        for field in SEMANTIC_FIELDS:
            if semantic.get(field) in {None, "", "unavailable"}:
                unavailable[field] += 1
            confidence_by_field[field].append(CONFIDENCE_VALUES.get(str(semantic.get("semantic_confidence", "unavailable")).lower(), 0.0))
        for agreement in item.agreements:
            if agreement.result == "incorrect":
                wrong_fields[agreement.field] += 1
                category_failures[item.category] += 1
        creator = item.report.get("creator_report", {}) or {}
        validation = creator.get("evidence_validation", {}) or {}
        if not validation.get("benchmark_supported"):
            benchmark_failures[str(validation.get("label") or "benchmark unavailable")] += 1
        opportunity = (creator.get("biggest_opportunity") or {}).get("title")
        if opportunity:
            recommendations[opportunity] += 1
        for experiment in creator.get("experiments", []) or []:
            experiments[str(experiment.get("title") or "untitled")] += 1
        for section in ("opening_snapshot", "intro_timeline", "whats_working", "biggest_opportunity", "experiments"):
            if not creator.get(section):
                empty_sections[section] += 1
    lowest = sorted(((field, round(sum(values) / len(values), 3)) for field, values in confidence_by_field.items() if values), key=lambda item: item[1])
    return {
        "most_common_wrong_semantic_field": wrong_fields.most_common(1),
        "most_common_unavailable_field": unavailable.most_common(1),
        "most_common_benchmark_failure": benchmark_failures.most_common(1),
        "most_common_category_failure": category_failures.most_common(1),
        "most_repeated_recommendation": recommendations.most_common(1),
        "most_common_experiment": experiments.most_common(1),
        "semantic_fields_with_lowest_confidence": lowest,
        "creator_sections_most_often_empty": empty_sections.most_common(),
    }
