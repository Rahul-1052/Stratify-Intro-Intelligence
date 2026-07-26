"""Conservative deterministic report-quality warnings."""

import re

MAJOR_KEYS = ("opening_snapshot", "creative_understanding", "biggest_opportunity")
PERFORMANCE = re.compile(r"\b(increase|improve|boost|guarantee|drive)\b.{0,24}\b(retention|views|performance|engagement)\b", re.I)
PSYCHOLOGY = re.compile(r"\b(viewers?|audience)\s+(will|want|feel|prefer|love|hate|expect)\b", re.I)
GENERIC = re.compile(
    r"\b(make it better|improve the hook|(?:be|make it) more engaging|add value|"
    r"increase energy|add more movement|use stronger visuals|make the pacing faster)\b",
    re.I,
)


def _creator(report):
    return report.get("creator_report") or {}


def _text(value):
    if isinstance(value, dict):
        return " ".join(_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_text(item) for item in value)
    return str(value or "")


def warning(code, section, message, evidence=""):
    return {"code": code, "severity": "warning", "section": section,
            "message": message, "evidence": evidence,
            "classification": "automated heuristic review; requires human review"}


def run_quality_checks(report):
    if not isinstance(report, dict):
        return [warning("malformed_report", "report", "Report payload is not an object.")]
    creator = _creator(report)
    findings = []
    required = ("opening_snapshot", "creative_understanding", "biggest_opportunity", "experiments", "confidence_summary")
    for key in required:
        if key not in creator:
            findings.append(warning("missing_section", key, f"Creator report is missing {key}."))
    experiments = creator.get("experiments") or []
    opportunity = creator.get("biggest_opportunity") or {}
    confidence = creator.get("confidence_summary") or {}
    if len(experiments) > 3:
        findings.append(warning("experiment_count_padding", "experiments", "More than three experiments are presented.", str(len(experiments))))
    if not opportunity.get("supported") and experiments:
        findings.append(warning("no_opportunity_has_experiments", "experiments", "An unsupported opportunity still presents experiments."))
    if "abstention" in _text(creator).lower() and experiments:
        findings.append(warning("abstention_has_advice", "experiments", "An abstention report also presents advice."))
    text_state = str(confidence.get("text_evidence") or "").lower()
    for index, experiment in enumerate(experiments):
        if not isinstance(experiment, dict) or not all(experiment.get(k) for k in ("title", "change", "confidence")):
            findings.append(warning("malformed_experiment", "experiments", f"Experiment {index + 1} is incomplete."))
        dimension = str(experiment.get("structural_dimension") or experiment.get("dimension") or "").lower()
        source = str(experiment.get("source") or "").lower()
        if ("text" in dimension or "text" in source) and text_state in {"limited", "isolated", "unknown", "unavailable"}:
            findings.append(warning("unsupported_text_experiment", "experiments", "Text-derived advice exceeds the available text evidence."))
        timing = experiment.get("target_timing")
        timing_applicable = not isinstance(timing, dict) or timing.get("applicability") != "not_applicable"
        if timing_applicable and not timing:
            findings.append(warning("missing_target_timing", "experiments", f"Experiment {index + 1} has no applicable target timing."))
        if not experiment.get("variable"):
            findings.append(warning("missing_measurable_variable", "experiments", f"Experiment {index + 1} has no measurable variable."))
        if not (experiment.get("control") or experiment.get("what_stays_constant")):
            findings.append(warning("missing_control", "experiments", f"Experiment {index + 1} has no stated control."))
        if not (experiment.get("exact_execution") or experiment.get("change")):
            findings.append(warning("missing_execution_instruction", "experiments", f"Experiment {index + 1} has no execution instruction."))
        if not (experiment.get("source_finding_ids") or experiment.get("evidence_key")):
            findings.append(warning("missing_evidence_reference", "experiments", f"Experiment {index + 1} has no evidence reference."))
        if not experiment.get("invalidation_criteria"):
            findings.append(warning("missing_invalidation_criteria", "experiments", f"Experiment {index + 1} has no invalidation criteria."))
        if experiment.get("benchmark_supported") and not (
            (report.get("benchmark") or {}).get("benchmark_quality") or {}
        ).get("eligible_for_directional_learning"):
            findings.append(warning("false_benchmark_support", "experiments", f"Experiment {index + 1} claims unavailable benchmark support."))
        variable = str(experiment.get("variable") or "")
        if re.search(r",|\band\b|\+|/", variable, re.I):
            findings.append(warning("multiple_simultaneous_variables", "experiments", f"Experiment {index + 1} may change multiple variables.", variable))
    signatures = []
    for index, experiment in enumerate(experiments):
        signature = (
            str(experiment.get("structural_dimension") or "").strip().lower(),
            str(experiment.get("variable") or experiment.get("change") or "").strip().lower(),
        )
        if signature in signatures:
            findings.append(warning("duplicate_experiment", "experiments", f"Experiment {index + 1} duplicates an earlier test.", str(signature)))
        signatures.append(signature)
    all_text = _text(creator)
    if PERFORMANCE.search(all_text):
        findings.append(warning("unsupported_performance_claim", "recommendation", "Recommendation language may promise performance without outcome evidence."))
    if re.search(r"\bretention\b", all_text, re.I) and not report.get("outcome_evidence"):
        findings.append(warning("retention_without_evidence", "recommendation", "Retention is mentioned without outcome evidence."))
    if PSYCHOLOGY.search(all_text):
        findings.append(warning("audience_psychology_claim", "interpretation", "Audience psychology is asserted without direct evidence."))
    if GENERIC.search(all_text):
        findings.append(warning("generic_recommendation", "recommendation", "Recommendation language may be too generic."))
    sections = [_text(creator.get(key)) for key in MAJOR_KEYS]
    sentences = [set(re.findall(r"[^.!?]{45,}[.!?]", section)) for section in sections]
    if any(sentences[i] & sentences[j] for i in range(len(sentences)) for j in range(i + 1, len(sentences))):
        findings.append(warning("repeated_long_sentence", "report", "A long sentence repeats across major sections."))
    status = str(report.get("status") or "").lower()
    coverage = str(confidence.get("evidence_coverage") or confidence.get("evidence_completeness") or "").lower()
    if status == "success" and coverage in {"none", "unavailable"}:
        findings.append(warning("status_evidence_mismatch", "confidence", "Successful status conflicts with unavailable evidence."))
    labels = {str(v).lower() for k, v in confidence.items() if "confidence" in k}
    if "high" in labels and "limited" in labels and not creator.get("confidence_breakdown"):
        findings.append(warning("conflicting_confidence", "confidence", "High and limited confidence labels coexist; verify that dimensions are clearly separated."))
    if not creator.get("limitations") and (status == "partial" or text_state in {"limited", "unknown", "unavailable"}):
        findings.append(warning("missing_limitation", "limitations", "Limited evidence is not disclosed in the Creator report."))
    return findings


def issue_signature(issue):
    return "|".join(str(issue.get(key, "")).strip().lower() for key in ("category", "section", "short_description"))
