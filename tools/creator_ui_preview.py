"""Local visual QA harness for Creator Product Readiness states."""

import streamlit as st

from core.creator_report import build_creator_report
from core.creator_presentation import creator_confidence_presentation, creator_status_message
from core.memory.models import AnalysisRecord
from core.memory.reconstruction import reconstruct_creator_report
from ui.components import ProgressPresenter
from ui.memory import _fallback_saved_report, render_current_comparison, render_save_controls
from ui.report import render_report
from ui.theme import apply_theme
from ui.workspace import render_module_cards, render_platform_header, render_workspace_intro


def _frames(text=False, sparse=False):
    count = 1 if sparse else 4
    return [{
        "timestamp": index, "human_presence": True, "subject_count": 1,
        "scene_type": "person_focused", "visual_energy": "low",
        "text_overlay": text, "text_overlay_confidence": "limited",
    } for index in range(count)]


def _report(text=False, sparse=False):
    report = {"status": "success", "warnings": [], "video": {"title": "Creator report preview"},
              "vision": {"frame_observations": _frames(text, sparse)}, "benchmark": {},
              "patterns": {}, "reasoning": {}, "evidence": {}}
    report["creator_report"] = build_creator_report(report)
    return report


def _status(report):
    creator = report["creator_report"]
    presentation = creator_confidence_presentation(report, creator)
    message = creator_status_message(
        presentation, bool(creator["biggest_opportunity"].get("supported"))
    )
    if presentation["analysis_status"]["value"] == "Completed":
        st.success(message)
    else:
        st.info(message)


class _NoProfileMemory:
    def profile(self):
        return None


class _SavedMemory:
    def profile(self):
        return {"id": "fixture"}

    def dashboard(self):
        return {"counts": {"analyses": 0}}


def _memory_record(partial=False):
    normalized = {
        "id": "fixture-analysis", "video_id": "fixture-video",
        "analysis_version": "creator-product-v1",
        "created_at": "2026-07-20T14:30:00+00:00",
        "snapshot": {} if partial else {"summary": "A creator appears first, then establishes the surrounding context."},
        "creative_structure": {
            "opening_strategy": "subject-first", "structural_rhythm": "two phases",
            "reveal_pattern": "anchor established immediately",
        },
        "creative_understanding": {"summary": "The creator leads before the setting expands."},
        "reasoning_summary": {"status": "success", "additional_observations": []},
        "opportunity": {
            "title": "Test the timing of the context reveal",
            "summary": "The subject is established before the setting becomes clear.",
            "why_test": "A controlled timing alternative can compare two readable structures.",
            "current_structure": "Subject before surrounding context",
            "proposed_alternative": "Reveal the same context one phase earlier",
            "supported": True, "confidence": "moderate",
            "limitation": "This is structural evidence, not a performance prediction.",
        },
        "experiments": [{
            "title": "Move the context reveal", "hypothesis": "Earlier context changes the opening sequence.",
            "change": "Reveal the existing setting one phase earlier.",
            "what_stays_constant": "Keep footage, audio, message, and duration unchanged.",
            "version_a": "Keep the subject-first order.", "version_b": "Reveal context one phase earlier.",
            "support": "The saved structure contains two distinct phases.", "confidence": "moderate",
            "limitation": "No outcome evidence is stored.", "source": "Observation-backed",
        }],
        "confidence_summary": {} if partial else {
            "analysis_completeness": "complete", "evidence_confidence": "moderate",
            "recommendation_confidence": "moderate", "text_evidence": "limited",
            "plain_language": "Visual structure is available, but text-like evidence remains limited.",
        },
        "evidence_limitations": ["Written-information evidence was limited."],
        "analysis_completeness": "partial" if partial else "complete",
        "opening_strategy": "subject-first", "primary_visual_focus": "person",
        "progression_style": "two phases", "subject_timing": "anchor established immediately",
        "subject_presence": "single_subject", "multiple_subjects": False,
        "written_information_state": "limited", "recommendation_state": "supported",
        "recommendation_confidence": "moderate",
    }
    return AnalysisRecord(**normalized)


st.set_page_config(page_title="Stratify visual QA", layout="wide")
apply_theme()
state = st.query_params.get("state", "landing")
render_platform_header()
st.caption("Fixture-based UI validation · not a real-video replay")

if state == "landing":
    render_workspace_intro()
    st.text_input("YouTube video URL", placeholder="Paste a YouTube video URL", label_visibility="collapsed")
    st.button("Analyze this intro", type="primary", width="stretch")
    render_module_cards()
elif state == "loading":
    st.header("Analyzing the opening")
    progress = ProgressPresenter()
    progress.update("Observing visual changes")
elif state == "limited":
    report = _report(text=True)
    _status(report)
    render_report(report, "creator", {})
elif state == "no-opportunity":
    report = _report(sparse=True)
    _status(report)
    render_report(report, "creator", {})
elif state == "builder":
    report = _report(text=True)
    _status(report)
    render_report(report, "builder", {})
elif state == "cta":
    report = _report()
    _status(report)
    render_report(
        report, "creator", {},
        after_opportunity=lambda: render_save_controls(
            _NoProfileMemory(), report, object(), "creator"
        ),
    )
elif state == "saved":
    report = _report()
    _status(report)
    st.session_state["creator_memory_saved_analysis_id"] = "fixture-saved"
    render_report(
        report, "creator", {},
        after_opportunity=lambda: render_save_controls(
            _SavedMemory(), report, object(), "creator"
        ),
    )
elif state == "confidence":
    report = _report(text=True)
    _status(report)
    render_report(report, "creator", {})
elif state == "one-experiment":
    report = _report()
    creative = report["creator_report"]
    creative["biggest_opportunity"] = {
        "title": "Test a clearer first visual priority",
        "summary": "More than one visual anchor appears in the first phase.",
        "why_test": "This controlled change isolates visual hierarchy.",
        "current_structure": "Multiple visual anchors",
        "proposed_alternative": "Hold one existing anchor first",
        "confidence": "high", "source": "Observation-backed",
        "limitation": "No qualified benchmark comparison is available.",
        "supported": True,
    }
    creative["experiments"] = [{
        "title": "Lead with one visual anchor", "source": "Observation-backed",
        "hypothesis": "One initial anchor changes the opening hierarchy.",
        "change": "Hold the existing primary subject before other elements appear.",
        "what_stays_constant": "Footage, audio, message, and duration.",
        "version_a": "Keep the current simultaneous introduction.",
        "version_b": "Introduce the primary subject first.",
        "support": "Repeated multi-subject evidence appears in the first phase.",
        "confidence": "moderate", "limitation": "This does not predict performance.",
    }]
    _status(report)
    render_report(report, "creator", {})
elif state == "history-full":
    restored = reconstruct_creator_report(
        _memory_record(), {"title": "Fixture saved project"}, revision=2
    )
    saved = restored["report"]["saved_history"]
    st.info(
        f"Saved historical analysis · originally analyzed {saved['analysis_date'][:10]} "
        f"· revision {saved['revision']} · no analysis rerun"
    )
    render_report(restored["report"], "creator", {})
elif state == "history-partial":
    restored = reconstruct_creator_report(
        _memory_record(partial=True), {"title": "Fixture partial project"}, revision=1
    )
    _fallback_saved_report(restored, "creator")
elif state == "comparison":
    current = _report()
    render_report(current, "creator", {})
    render_current_comparison({
        "state": "partially_matches_history",
        "message": "The subject-first opening is familiar, while the two-phase progression differs from most saved analyses.",
        "evidence": {"baseline_analyses": 4},
    })
else:
    report = _report()
    creative = report["creator_report"]
    creative["biggest_opportunity"] = {
        "title": "Test a clearer first visual priority", "summary": "The current opening introduces more than one priority at once.",
        "why_test": "A controlled alternative can test whether one initial priority makes the structure easier to follow.",
        "current_structure": "Multiple priorities begin together", "proposed_alternative": "Hold one existing priority first",
        "keep_constant": "Keep footage, audio, message, and duration unchanged.", "confidence": "moderate",
        "limitation": "No qualified benchmark set was available.", "supported": True,
    }
    creative["experiments"] = [{
        "title": "Lead with one visual priority", "source": "Observation-backed", "hypothesis": "One initial priority may make the sequence easier to describe.",
        "change": "Hold the existing primary subject before the second element appears.", "what_stays_constant": "Footage, audio, message, and duration.",
        "version_a": "Keep the current simultaneous introduction.", "version_b": "Introduce the primary subject first.",
        "support": "Repeated visual evidence shows competing early priorities.", "confidence": "moderate",
        "limitation": "This tests clarity; it does not predict retention.",
    }]
    _status(report)
    render_report(report, "creator", {})
