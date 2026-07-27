from html import escape

import streamlit as st

from ui.advanced import render_advanced_analysis
from ui.creator_report_v4 import render_creator_report_v4
from core.creator_report import build_creator_report
from core.creator_presentation import creator_confidence_presentation
from ui.components import (
    clean_value,
    confidence_badge,
    empty_state,
    info_card,
    render_card_grid,
    safe,
    section_heading,
)


def _intro_observation(report):
    intro = report.get("intro_observation", {})
    if not isinstance(intro, dict):
        return {}, {}
    observation = intro.get("observation") or intro.get("observations") or {}
    return intro, observation if isinstance(observation, dict) else {}


def _first_value(mapping, *keys):
    for key in keys:
        value = clean_value(mapping.get(key))
        if value:
            return value
    return ""


def _strongest_recommendation(patterns):
    experiments = patterns.get("top_creator_experiments", []) or []
    recommendations = patterns.get("recommendations", []) or []
    return (experiments or recommendations or [{}])[0]


def _friendly_verdict(text):
    value = clean_value(text)
    if not value:
        return (
            "There is not enough reliable comparison evidence to position this "
            "opening yet."
        )
    replacements = {
        "benchmark evidence": "comparison evidence",
        "benchmark sample": "comparison set",
        "benchmark group": "comparison set",
        "benchmarks": "comparable videos",
        "qualified candidates": "reliable comparisons",
        "qualification": "evidence quality",
    }
    for source, replacement in replacements.items():
        value = value.replace(source, replacement).replace(
            source.title(), replacement.title()
        )
    return value


def _target_timing(item):
    timing = item.get("target_timing")
    if not isinstance(timing, dict):
        return ""
    if timing.get("applicability") == "not_applicable":
        return clean_value(timing.get("reason")) or "No narrower reliable timestamp applies."
    start, end = timing.get("start_time"), timing.get("end_time")
    if start is None or end is None:
        return ""
    return f"{float(start):.1f}s–{float(end):.1f}s"


def render_next_best_test(patterns):
    recommendation = _strongest_recommendation(patterns)
    title = clean_value(recommendation.get("title"))
    suggested_test = clean_value(recommendation.get("suggested_test"))

    st.markdown('<div class="stratify-report-head"></div>', unsafe_allow_html=True)
    if not title and not suggested_test:
        st.markdown(
            """
            <div class="stratify-hero-card">
                <div class="stratify-eyebrow">Next best test</div>
                <h2>Your opening still supports a controlled creative test.</h2>
                <p>Use direct intro observations for the next experiment; benchmark
                validation can be added later when reliable comparisons exist.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return ""

    why = clean_value(recommendation.get("why_it_matters"))
    st.markdown(
        f"""
        <div class="stratify-hero-card">
            <div class="stratify-eyebrow">Next best test</div>
            <h2>{escape(title or "Evidence-backed experiment")}</h2>
            <p><strong>Try this:</strong> {escape(suggested_test or why)}</p>
            {f'<p class="stratify-muted">{escape(why)}</p>' if why and why != suggested_test else ''}
            <div style="margin-top:1.15rem">{confidence_badge(recommendation.get('confidence'))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return title


def render_final_verdict(patterns):
    section_heading(
        "Overall assessment",
        "A plain-language read of how confidently this opening can be positioned.",
    )
    verdict = _friendly_verdict(patterns.get("final_verdict"))
    st.markdown(
        f'<div class="stratify-card"><p style="font-size:1.08rem;color:#1f2937">'
        f"{escape(verdict)}</p></div>",
        unsafe_allow_html=True,
    )


def render_observations(report):
    intro, observation = _intro_observation(report)
    features = report.get("feature_report", {}).get("feature_summary", {}) or {}
    cards = []
    observation_fields = (
        ("Opening", ("opening_summary",)),
        ("Hook", ("hook_type", "opening_action_type")),
        ("Subject", ("main_subject", "subject_clarity")),
        ("Story promise", ("story_promise", "payoff_teased")),
        ("Viewer question", ("viewer_question", "curiosity_gap")),
        ("First impression", ("first_impression", "first_time_viewer_reaction")),
    )
    for label, keys in observation_fields:
        value = _first_value(observation, *keys) or _first_value(features, *keys)
        if value:
            cards.append(info_card(label, value))

    section_heading(
        "What Stratify observed",
        "The opening signals visible in the intro itself, before performance is considered.",
    )
    if cards:
        render_card_grid(cards)
    else:
        empty_state(
            "Visual observation was limited",
            "Stratify continued with the evidence that was available.",
        )

    confidence = _first_value(observation, "confidence") or clean_value(
        intro.get("confidence")
    )
    if confidence:
        st.markdown(
            f'<div style="margin-top:1rem">{confidence_badge(confidence)}</div>',
            unsafe_allow_html=True,
        )


def _comparison_card(item):
    label = clean_value(item.get("label")) or "Observed pattern"
    user_value = clean_value(item.get("user_value"))
    top_value = clean_value(item.get("top_dominant_value"))
    lower_value = clean_value(item.get("lower_dominant_value"))
    explanation = clean_value(item.get("explanation"))
    values = []
    for title, value in (
        ("Your opening", user_value),
        ("Stronger intros", top_value),
        ("Lower-performing intros", lower_value),
    ):
        if value:
            values.append(
                '<div class="stratify-compare-value">'
                f'<span class="stratify-label">{escape(title)}</span>'
                f"<strong>{escape(value)}</strong></div>"
            )
    return (
        '<div class="stratify-card" style="margin-bottom:1rem">'
        f"<h3>{escape(label.title())}</h3>"
        f'<div class="stratify-compare-grid">{"".join(values)}</div>'
        f"{f'<p>{escape(explanation)}</p>' if explanation else ''}"
        "</div>"
    )


def render_successful_patterns(patterns):
    opportunities = patterns.get("strongest_opportunities", []) or []
    if not opportunities:
        opportunities = (
            patterns.get("missing_winning_features", [])
            + patterns.get("risk_signals", [])
        )

    section_heading(
        "What stronger intros did differently",
        "Only differences supported by the qualified comparison set appear here.",
    )
    if not opportunities:
        empty_state(
            "Direct observations remain available",
            "The comparison set did not add a directional pattern, so no benchmark claim is made.",
        )
        return
    for item in opportunities[:5]:
        st.markdown(_comparison_card(item), unsafe_allow_html=True)


def render_experiments(patterns, featured_title):
    experiments = patterns.get("top_creator_experiments", []) or []
    if not experiments:
        experiments = patterns.get("recommendations", []) or []
    remaining = [
        item
        for item in experiments
        if not featured_title
        or clean_value(item.get("title")).casefold() != featured_title.casefold()
    ]

    section_heading(
        "Recommended experiments",
        "Practical tests supported by the current evidence—not generic advice.",
    )
    if not remaining:
        empty_state(
            "No additional supported experiments",
            (
                "The strongest supported experiment is shown above."
                if featured_title
                else "Use the observation-backed experiments in the creator report."
            ),
        )
        return

    cards = []
    for item in remaining[:4]:
        title = clean_value(item.get("title")) or "Evidence-backed experiment"
        suggested = clean_value(item.get("suggested_test"))
        why = clean_value(item.get("why_it_matters")) or clean_value(
            item.get("evidence")
        )
        cards.append(
            '<div class="stratify-card">'
            f"<h3>{escape(title)}</h3>"
            f"{f'<p><strong>Test:</strong> {escape(suggested)}</p>' if suggested else ''}"
            f"{f'<p>{escape(why)}</p>' if why else ''}"
            f'<div style="margin-top:1rem">{confidence_badge(item.get("confidence"))}</div>'
            "</div>"
        )
    render_card_grid(cards, columns=2)


def render_confidence(patterns):
    section_heading(
        "Evidence quality",
        "How much weight to place on the comparisons and experiments above.",
    )
    confidence = clean_value(patterns.get("confidence")) or "Low"
    reason = clean_value(patterns.get("confidence_reason")) or (
        "Not enough comparable intro evidence was available for a stronger conclusion."
    )
    st.markdown(
        '<div class="stratify-card">'
        f"{confidence_badge(confidence)}"
        f'<p style="margin-top:0.9rem">{escape(_friendly_verdict(reason))}</p>'
        "</div>",
        unsafe_allow_html=True,
    )


def render_report(report, product_mode, version_metadata, after_opportunity=None):
    creator = report.get("creator_report") or build_creator_report(report, product_mode=product_mode)
    presentation = creator_confidence_presentation(report, creator)
    render_creator_report_v4(
        report, creator, presentation, product_mode, version_metadata,
        after_opportunity=after_opportunity,
    )
