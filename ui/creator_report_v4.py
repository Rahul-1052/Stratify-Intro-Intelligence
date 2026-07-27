"""Premium Creator Report V4 presentation over existing Intelligence V3 output."""

import json
from html import escape

import streamlit as st

from ui.advanced import render_advanced_analysis
from ui.components import clean_value, empty_state, section_heading


EVENT_PRESENTATION = {
    "subject_count_change": ("👤", "Subject Appears"),
    "dominant_subject_change": ("◎", "Subject Focus Changes"),
    "scene_change": ("▣", "Scene Change"),
    "lighting_change": ("☀", "Lighting Shift"),
    "text_overlay_change": ("T", "Text Appears"),
    "composition_change": ("◫", "Composition Change"),
    "motion_state_change": ("↗", "Motion Changes"),
    "visual_energy_change": ("◆", "Visual Energy Changes"),
    "focal_region_change": ("⊙", "Focal Region Changes"),
}


def _confidence_value(creator, key, fallback="limited"):
    breakdown = creator.get("confidence_breakdown") or {}
    value = breakdown.get(key)
    if not value:
        summary = creator.get("confidence_summary") or {}
        aliases = {
            "observation_confidence": "evidence_confidence",
            "interpretation_confidence": "evidence_confidence",
            "recommendation_confidence": "recommendation_confidence",
        }
        value = summary.get(aliases[key], fallback)
    return clean_value(value) or fallback


def _confidence_explanation(key, value):
    level = str(value).lower()
    phrases = {
        "observation_confidence": {
            "high": "Repeated timestamped measurements support the observations.",
            "moderate": "Multiple sampled measurements support the observations.",
            "limited": "The available samples support only cautious observations.",
        },
        "interpretation_confidence": {
            "high": "The qualified observations form a consistent structural pattern.",
            "moderate": "The observations support a plausible pattern with stated limitations.",
            "limited": "The observations do not support a strong structural interpretation.",
        },
        "recommendation_confidence": {
            "high": "Qualified evidence supports an isolated creative test.",
            "moderate": "Direct evidence supports testing one controlled variable.",
            "limited": "The evidence supports only a cautious test or an abstention.",
            "no supported recommendation": "No isolated creative change is justified.",
        },
    }
    return phrases[key].get(level, phrases[key]["limited"])


def _benchmark_available(report, creator):
    validation = creator.get("evidence_validation") or {}
    quality = (report.get("benchmark") or {}).get("benchmark_quality") or {}
    return bool(
        validation.get("benchmark_supported")
        or quality.get("eligible_for_directional_learning")
    )


def _direct_evidence_status(report):
    intelligence = report.get("intelligence_v3") or {}
    findings = intelligence.get("findings") or []
    if any(
        item.get("availability_state") == "available_and_qualified"
        for item in findings if isinstance(item, dict)
    ):
        return "Available"
    if bool((report.get("vision") or {}).get("frame_observations")):
        return "Limited"
    return "Unavailable"


def _direct_evidence_available(report):
    return _direct_evidence_status(report) == "Available"


def _verdict(creator):
    opportunity = creator.get("biggest_opportunity") or {}
    if opportunity.get("supported"):
        summary = clean_value(opportunity.get("summary"))
        title = clean_value(opportunity.get("title"))
        return summary or (
            f"The strongest supported opportunity is to {title.lower()}."
            if title else "The opening supports one controlled creative test."
        )
    snapshot = clean_value((creator.get("opening_snapshot") or {}).get("summary"))
    return snapshot or "The available evidence does not support a creative change yet."


def render_hero(report, creator):
    opportunity = creator.get("biggest_opportunity") or {}
    supported = bool(opportunity.get("supported"))
    benchmark = _benchmark_available(report, creator)
    direct = _direct_evidence_status(report)
    metrics = (
        ("Observation", _confidence_value(creator, "observation_confidence")),
        ("Interpretation", _confidence_value(creator, "interpretation_confidence")),
        ("Recommendation", _confidence_value(
            creator, "recommendation_confidence",
            "limited" if supported else "No supported recommendation",
        )),
        ("Benchmarks", "Available" if benchmark else "Unavailable"),
        ("Direct evidence", direct),
    )
    section_heading("Hero Summary", "Your opportunity, evidence, and next decision at a glance.")
    st.markdown(
        '<div class="stratify-v4-hero">'
        '<div class="stratify-eyebrow">Opening verdict</div>'
        f'<h2>{escape(_verdict(creator))}</h2>'
        f'<div class="stratify-v4-opportunity"><span>Primary opportunity</span>'
        f'<strong>{escape(clean_value(opportunity.get("title")) or "No supported change yet")}</strong></div>'
        '<div class="stratify-v4-metrics">'
        + "".join(
            f'<div><span>{escape(label)}</span><strong>{escape(value.title())}</strong></div>'
            for label, value in metrics
        )
        + '</div></div>',
        unsafe_allow_html=True,
    )
    source_type = clean_value(
        (creator.get("source_provenance") or {}).get("source_type")
        or (report.get("source_context") or {}).get("source_type")
    )
    if source_type in {"uploaded_file", "cached_local_clip"}:
        st.info(
            "Local source analysis · qualified benchmark context is unavailable. "
            "This report uses direct evidence from the supplied video only."
        )


def story_events(report):
    intelligence = report.get("intelligence_v3") or {}
    raw_events = intelligence.get("meaningful_change_events") or []
    grouped = {}
    for item in raw_events:
        if not isinstance(item, dict):
            continue
        event_type = clean_value(item.get("event_type"))
        timestamp = float(item.get("timestamp") or 0)
        previous, current = item.get("previous_state"), item.get("new_state")
        icon, title = EVENT_PRESENTATION.get(
            event_type, ("•", clean_value(event_type).replace("_", " ").title())
        )
        if event_type == "text_overlay_change":
            title = "Text Appears" if current is True else "Text Disappears"
        elif event_type == "subject_count_change":
            title = "Subject Appears" if float(current or 0) > float(previous or 0) else "Subject Count Changes"
        grouped.setdefault(timestamp, []).append({
            "timestamp": timestamp, "icon": icon, "title": title,
            "explanation": f"{clean_value(previous)} → {clean_value(current)}",
            "strength": clean_value(item.get("evidence_strength")) or "limited",
            "event_type": event_type,
        })
    priority = {
        "subject_count_change": 0, "scene_change": 1, "text_overlay_change": 2,
        "composition_change": 3, "lighting_change": 4, "focal_region_change": 5,
        "motion_state_change": 6, "visual_energy_change": 7,
    }
    events = []
    for timestamp, candidates in sorted(grouped.items()):
        selected = min(candidates, key=lambda item: priority.get(item["event_type"], 20))
        if len(candidates) > 1:
            selected = {
                **selected,
                "title": (
                    selected["title"] if selected["event_type"] in {
                        "subject_count_change", "scene_change", "text_overlay_change"
                    } else "Information Update"
                ),
                "explanation": (
                    selected["explanation"]
                    + f" {len(candidates) - 1} other visual dimension(s) changed at this timestamp."
                ),
            }
        events.append(selected)
    if events:
        first = events[0]
        events.insert(0, {
            "timestamp": first["timestamp"], "icon": "◇", "title": "First Visual Change",
            "explanation": "The first qualified meaningful visual update occurs here.",
            "strength": first["strength"], "event_type": "first_visual_change",
        })
    stable = (intelligence.get("visual_change_timing") or {}).get(
        "longest_stable_interval"
    ) or {}
    duration = float(stable.get("duration") or 0)
    if duration > 0:
        start, end = float(stable.get("start_time") or 0), float(stable.get("end_time") or 0)
        events.append({
            "timestamp": start, "icon": "—", "title": "Stable Segment",
            "explanation": f"The longest measured stable segment continues to {end:.1f}s ({duration:.1f}s).",
            "strength": "measured", "event_type": "stable_segment",
        })
    events.sort(key=lambda item: (item["timestamp"], item["title"]))
    if len(events) > 9:
        events = events[:5] + events[-4:]
    return events


def render_story(report):
    section_heading("Story of the Intro", "A chronological view of observable visual development.")
    events = story_events(report)
    if not events:
        empty_state(
            "No qualified visual events",
            "The available evidence did not establish a chronological visual change.",
        )
        return
    st.markdown(
        '<div class="stratify-v4-timeline">'
        + "".join(
            '<div class="stratify-v4-event">'
            f'<div class="event-icon">{escape(item["icon"])}</div>'
            f'<div class="event-time">{item["timestamp"]:.1f}s</div>'
            f'<div><strong>{escape(item["title"])}</strong>'
            f'<p>{escape(item["explanation"])}</p></div></div>'
            for item in events
        )
        + '</div>',
        unsafe_allow_html=True,
    )


def strongest_finding(report, creator):
    findings = [
        item for item in (report.get("intelligence_v3") or {}).get("findings", [])
        if isinstance(item, dict)
    ]
    experiments = creator.get("experiments") or []
    source_ids = (experiments[0].get("source_finding_ids") or []) if experiments else []
    selected = next(
        (item for item in findings if item.get("finding_id") in source_ids),
        None,
    )
    if not selected:
        selected = next(
            (item for item in findings
             if item.get("availability_state") == "available_and_qualified"),
            None,
        )
    return selected


def _finding_title(finding):
    return clean_value(finding.get("observation_type")).replace("_", " ").title()


def _finding_measurement(finding):
    measured = finding.get("measured_value")
    if isinstance(measured, dict):
        timing = measured.get("longest_stable_interval")
        if timing:
            return (
                f"Longest stable interval: {float(timing.get('start_time') or 0):.1f}s–"
                f"{float(timing.get('end_time') or 0):.1f}s "
                f"({float(timing.get('duration') or 0):.1f}s)."
            )
        return "; ".join(
            f"{clean_value(key).replace('_', ' ')}: {clean_value(value)}"
            for key, value in list(measured.items())[:3]
            if value is not None and value != "" and value != []
        )
    return clean_value(measured)


def render_strongest_finding(report, creator):
    section_heading("Strongest Finding", "The single finding most relevant to the primary decision.")
    finding = strongest_finding(report, creator)
    opportunity = creator.get("biggest_opportunity") or {}
    if not finding:
        empty_state(
            "No qualified finding to surface",
            clean_value(opportunity.get("limitation"))
            or "The available evidence does not justify a strongest finding.",
        )
        return
    limitations = finding.get("limitations") or []
    st.markdown(
        '<div class="stratify-v4-finding">'
        f'<span class="stratify-badge">{escape(clean_value(finding.get("evidence_strength")).title())} evidence</span>'
        f'<h3>{escape(_finding_title(finding))}</h3>'
        f'<p><strong>Evidence:</strong> {escape(_finding_measurement(finding))}</p>'
        f'<p><strong>Timestamp:</strong> {float(finding.get("start_time") or 0):.1f}s–'
        f'{float(finding.get("end_time") or 0):.1f}s</p>'
        f'<p><strong>Why it matters:</strong> {escape(clean_value(opportunity.get("why_test")) or "It informs the primary controlled decision.")}</p>'
        f'<p class="stratify-muted"><strong>Limitation:</strong> '
        f'{escape(clean_value(limitations[0]) if limitations else clean_value(opportunity.get("limitation")))}</p>'
        '</div>',
        unsafe_allow_html=True,
    )


def _target_timing(item):
    timing = item.get("target_timing")
    if not isinstance(timing, dict):
        return "Not specified"
    if timing.get("applicability") == "not_applicable":
        return clean_value(timing.get("reason")) or "No narrower reliable timestamp applies."
    if timing.get("start_time") is None or timing.get("end_time") is None:
        return "Not specified"
    return f"{float(timing['start_time']):.1f}s–{float(timing['end_time']):.1f}s"


def render_primary_experiment(creator):
    section_heading("Primary Experiment", "One isolated test supported by the current evidence.")
    experiments = creator.get("experiments") or []
    opportunity = creator.get("biggest_opportunity") or {}
    if not experiments or not opportunity.get("supported"):
        st.markdown(
            '<div class="stratify-v4-abstention">'
            '<div class="stratify-eyebrow">Evidence-aware abstention</div>'
            '<h3>No experiment is supported yet</h3>'
            f'<p>{escape(clean_value(opportunity.get("summary")) or "The evidence is insufficient for an isolated recommendation.")}</p>'
            f'<p><strong>Why:</strong> {escape(clean_value(opportunity.get("limitation")) or "A controlled alternative cannot be justified.")}</p>'
            '<p class="stratify-muted">Keep the current edit until clearer direct or comparative evidence is available.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        return
    item = experiments[0]
    limitation = clean_value(item.get("limitation"))
    rows = (
        ("Variable", item.get("variable") or item.get("structural_dimension")),
        ("Keep constant", item.get("control") or item.get("what_stays_constant")),
        ("Target timing", _target_timing(item)),
        ("Execution", item.get("exact_execution") or item.get("change")),
        ("Expected observable change", item.get("expected_observable_change") or item.get("version_b")),
        ("Measurement plan", item.get("measurement_plan") or item.get("how_to_compare")),
        ("Evidence basis", item.get("evidence_basis") or item.get("support")),
        ("Limitations", limitation),
        ("Invalidation criteria", item.get("invalidation_criteria")),
    )
    st.markdown(
        '<div class="stratify-v4-experiment">'
        f'<span class="stratify-badge">{escape(clean_value(item.get("source")) or "Observation-backed")}</span>'
        f'<h2>{escape(clean_value(item.get("experiment_title") or item.get("title")) or "Controlled intro test")}</h2>'
        '<div class="stratify-v4-experiment-grid">'
        + "".join(
            f'<div><span>{escape(label)}</span><p>{escape(clean_value(value) or "Unavailable")}</p></div>'
            for label, value in rows
        )
        + '</div></div>',
        unsafe_allow_html=True,
    )


def render_confidence(creator):
    section_heading("Confidence Breakdown", "Observation, interpretation, and recommendation are evaluated separately.")
    dimensions = (
        ("Observation Confidence", "observation_confidence"),
        ("Interpretation Confidence", "interpretation_confidence"),
        ("Recommendation Confidence", "recommendation_confidence"),
    )
    st.markdown(
        '<div class="stratify-v4-confidence">'
        + "".join(
            '<div>'
            f'<span>{escape(label)}</span>'
            f'<strong>{escape(_confidence_value(creator, key).title())}</strong>'
            f'<p>{escape(_confidence_explanation(key, _confidence_value(creator, key)))}</p>'
            '</div>'
            for label, key in dimensions
        )
        + '</div>',
        unsafe_allow_html=True,
    )


def _benchmark_metrics(report):
    benchmark = report.get("benchmark") or {}
    quality = benchmark.get("benchmark_quality") or {}
    comparisons = (report.get("patterns") or {}).get("comparisons") or []
    comparison = comparisons[0] if comparisons else {}
    return {
        "Your Value": comparison.get("user_value", "Available in supporting comparison"),
        "Benchmark Median": comparison.get("benchmark_median")
        or comparison.get("top_dominant_value", "Available in supporting comparison"),
        "Difference": comparison.get("difference", "Directional comparison only"),
        "Sample Size": quality.get("sample_size") or benchmark.get("qualified_count")
        or len(benchmark.get("top_performers") or []) + len(benchmark.get("lower_performers") or []),
        "Agreement Count": quality.get("agreement_count", "Not reported"),
        "Evidence Strength": quality.get("confidence") or quality.get("label") or "Qualified",
    }


def render_benchmarks(report, creator):
    section_heading("Benchmarks", "Comparative evidence appears only when the quality gate passes.")
    if not _benchmark_available(report, creator):
        st.markdown(
            '<div class="stratify-v4-unavailable">'
            '<div class="event-icon">∅</div><div>'
            '<h3>Benchmark Unavailable</h3>'
            '<p>No qualified comparison set was available. The report uses direct evidence only.</p>'
            '</div></div>',
            unsafe_allow_html=True,
        )
        return
    metrics = _benchmark_metrics(report)
    st.markdown(
        '<div class="stratify-v4-benchmark">'
        + "".join(
            f'<div><span>{escape(label)}</span><strong>{escape(clean_value(value))}</strong></div>'
            for label, value in metrics.items()
        )
        + '</div>',
        unsafe_allow_html=True,
    )


def _json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def render_supporting_evidence(report):
    section_heading("Supporting Evidence", "Qualified evidence objects are available for inspection.")
    findings = [
        item for item in (report.get("intelligence_v3") or {}).get("findings", [])
        if isinstance(item, dict)
    ]
    if not findings:
        empty_state(
            "No qualified structured evidence objects",
            "The available evidence did not qualify a supporting finding.",
        )
        return
    for finding in findings:
        label = f"{_finding_title(finding)} · {float(finding.get('start_time') or 0):.1f}s–{float(finding.get('end_time') or 0):.1f}s"
        with st.expander(label, expanded=False):
            st.markdown(f"**Finding ID:** `{clean_value(finding.get('finding_id'))}`")
            st.markdown(f"**Observation:** {_finding_title(finding)}")
            st.markdown(f"**Measurements:** `{_json_text(finding.get('measured_value'))}`")
            st.markdown(f"**Confidence:** {clean_value(finding.get('evidence_strength')).title()}")
            st.markdown(f"**Availability:** {clean_value(finding.get('availability_state')).replace('_', ' ').title()}")
            st.markdown(f"**Qualification:** {clean_value(finding.get('qualification_result')).replace('_', ' ').title()}")
            st.markdown(f"**Supporting observations:** {len(finding.get('supporting_observations') or [])}")
            st.markdown(f"**Conflicting observations:** {len(finding.get('conflicting_observations') or [])}")
            limitations = finding.get("limitations") or []
            if limitations:
                st.markdown("**Limitations:** " + " ".join(clean_value(item) for item in limitations))


def render_trust_limitations(creator):
    section_heading("What Stratify Cannot Conclude", "Clear boundaries make the recommendation more trustworthy.")
    statements = [
        "No retention or performance prediction is made.",
        "No audience psychology or preference is inferred.",
        "No causal outcome is claimed from visual evidence.",
        "No benchmark support is claimed when the comparison quality gate is unavailable.",
    ]
    statements.extend(
        item for item in (creator.get("limitations") or [])
        if clean_value(item) not in statements
    )
    st.markdown(
        '<div class="stratify-v4-trust">'
        + "".join(f'<div><span>✓</span><p>{escape(clean_value(item))}</p></div>' for item in statements)
        + '</div>',
        unsafe_allow_html=True,
    )


def render_builder(report, creator, presentation, version_metadata):
    section_heading("Builder Diagnostics", "Internal traceability and raw measurements.")
    warning_payload = report.get("objective_warnings") or report.get("validation_warnings") or []
    with st.expander("Evidence objects and finding IDs", expanded=False):
        st.json((report.get("intelligence_v3") or {}).get("findings") or [])
    with st.expander("Confidence tree and timing metrics", expanded=False):
        st.json({
            "confidence": (report.get("intelligence_v3") or {}).get("confidence") or {},
            "timing": (report.get("intelligence_v3") or {}).get("visual_change_timing") or {},
            "cadence": (report.get("intelligence_v3") or {}).get("visual_cadence") or {},
        })
    with st.expander("Pipeline trace and diagnostics", expanded=False):
        st.json({
            "pipeline_trace": report.get("pipeline_trace") or report.get("trace") or {},
            "presentation": presentation.get("diagnostics") or {},
            "validation_warnings": warning_payload,
            "benchmark_diagnostics": report.get("benchmark") or {},
        })
    render_advanced_analysis(report, "builder", version_metadata)


def render_creator_report_v4(
    report, creator, presentation, product_mode, version_metadata,
    after_opportunity=None,
):
    render_hero(report, creator)
    if after_opportunity:
        after_opportunity()
    render_story(report)
    render_strongest_finding(report, creator)
    render_primary_experiment(creator)
    render_confidence(creator)
    render_benchmarks(report, creator)
    render_supporting_evidence(report)
    render_trust_limitations(creator)
    if product_mode == "builder":
        render_builder(report, creator, presentation, version_metadata)
