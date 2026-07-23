"""Local visual QA harness for Creator Product Readiness states."""

import streamlit as st

from core.creator_report import build_creator_report
from ui.components import ProgressPresenter
from ui.report import render_report
from ui.theme import apply_theme
from ui.workspace import render_platform_header, render_workspace_intro


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


st.set_page_config(page_title="Stratify visual QA", layout="wide")
apply_theme()
state = st.query_params.get("state", "landing")
render_platform_header()

if state == "landing":
    render_workspace_intro()
    st.text_input("YouTube video URL", placeholder="Paste a YouTube video URL", label_visibility="collapsed")
    st.button("Analyze this intro", type="primary", width="stretch")
elif state == "loading":
    st.header("Analyzing the opening")
    progress = ProgressPresenter()
    progress.update("Observing visual changes")
elif state == "limited":
    render_report(_report(text=True), "creator", {})
elif state == "no-opportunity":
    render_report(_report(sparse=True), "creator", {})
elif state == "builder":
    render_report(_report(text=True), "builder", {})
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
    render_report(report, "creator", {})
