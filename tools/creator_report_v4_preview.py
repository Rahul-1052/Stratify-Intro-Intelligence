"""Fixture/local-payload visual validation harness for Creator Report V4."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from ui.report import render_report
from ui.theme import apply_theme
from ui.workspace import render_platform_header


def _finding():
    return {
        "finding_id": "v3-change-timing",
        "observation_type": "meaningful_visual_change",
        "start_time": 0.0, "end_time": 8.0,
        "measured_value": {
            "time_to_first_change": 4.0, "change_count": 2,
            "longest_stable_interval": {
                "start_time": 0.0, "end_time": 4.0, "duration": 4.0,
            },
        },
        "evidence_strength": "moderate",
        "evidence_source": "fixture_sampled_video_frames",
        "supporting_observations": [{"timestamp": 4.0}],
        "conflicting_observations": [],
        "availability_state": "available_and_qualified",
        "qualification_result": "qualified",
        "limitations": ["Fixture measurements validate rendering only."],
        "provenance": "fixture_based_validation",
    }


def _fixture(benchmark=False, abstention=False):
    finding = _finding()
    experiment = {
        "title": "Move one meaningful visual update earlier",
        "experiment_title": "Move one meaningful visual update earlier",
        "source": "Benchmark-supported" if benchmark else "Observation-backed",
        "source_finding_ids": ["v3-change-timing"],
        "variable": "Timing of the first meaningful visual change",
        "control": "Keep script, speaker, duration, delivery, and other edits unchanged.",
        "target_timing": {
            "start_time": 1.0, "end_time": 1.5, "applicability": "applicable",
        },
        "exact_execution": "Add one visible composition change from 1.0s to 1.5s.",
        "change": "Add one visible composition change from 1.0s to 1.5s.",
        "expected_observable_change": "The revised opening contains one earlier visual update.",
        "measurement_plan": "Verify the first-change timestamp, then compare like-for-like outcomes.",
        "evidence_basis": (
            "Qualified comparison and direct temporal evidence."
            if benchmark else "Direct temporal evidence; no benchmark support."
        ),
        "confidence": "moderate",
        "limitation": "The experiment does not predict a performance outcome.",
        "invalidation_criteria": "The comparison is inconclusive if another creative variable changes.",
        "benchmark_supported": benchmark,
    }
    creator = {
        "opening_snapshot": {"summary": "The opening holds one state until its first visible update at 4.0s."},
        "creative_understanding": {"status": "fixture"},
        "biggest_opportunity": {
            "title": (
                "No supported structural change yet" if abstention
                else "Test an earlier meaningful visual update"
            ),
            "summary": (
                "The fixture contains insufficient evidence for an isolated change."
                if abstention else
                "The opening remains visually stable from 0.0s to 4.0s."
            ),
            "why_test": "The first measured visual update occurs at 4.0s.",
            "limitation": (
                "Only one weak sample is available." if abstention
                else "No outcome evidence establishes performance impact."
            ),
            "supported": not abstention,
        },
        "experiments": [] if abstention else [experiment],
        "confidence_breakdown": {
            "observation_confidence": "limited" if abstention else "moderate",
            "interpretation_confidence": "limited" if abstention else "moderate",
            "recommendation_confidence": "limited" if abstention else "moderate",
        },
        "confidence_summary": {
            "evidence_confidence": "limited" if abstention else "moderate",
            "recommendation_confidence": "limited" if abstention else "moderate",
            "text_evidence": "limited",
        },
        "evidence_validation": {
            "benchmark_supported": benchmark and not abstention,
        },
        "limitations": ["No audience psychology, performance prediction, or causal outcome evidence is available."],
    }
    quality = {
        "eligible_for_directional_learning": benchmark and not abstention,
        "sample_size": 8, "agreement_count": 6,
        "confidence": "moderate",
    }
    return {
        "status": "success", "creator_report": creator,
        "vision": {"frame_observations": [{"timestamp": 0}, {"timestamp": 4}, {"timestamp": 8}]},
        "intelligence_v3": {
            "version": "stratify-intelligence-v3",
            "findings": [] if abstention else [finding],
            "meaningful_change_events": [] if abstention else [{
                "timestamp": 4.0, "event_type": "composition_change",
                "previous_state": "wide", "new_state": "close",
                "evidence_strength": "moderate",
            }],
            "visual_change_timing": (
                {} if abstention else finding["measured_value"]
            ),
            "confidence": creator["confidence_breakdown"],
        },
        "benchmark": {
            "benchmark_quality": quality,
            "top_performers": [{} for _ in range(4)] if benchmark else [],
            "lower_performers": [{} for _ in range(4)] if benchmark else [],
        },
        "patterns": {
            "comparisons": [{
                "user_value": 4.0, "benchmark_median": 1.8,
                "difference": 2.2,
            }] if benchmark else [],
        },
        "source_context": {
            "source_type": "fixture",
            "provenance": "fixture_based_validation",
        },
    }


st.set_page_config(page_title="Creator Report V4 QA", layout="wide")
apply_theme()
render_platform_header()
state = st.query_params.get("state", "benchmark")
mode = st.query_params.get("mode", "creator")
payload_path = Path(os.getenv("STRATIFY_V4_LOCAL_REPORT", ""))

if state == "local" and payload_path.is_file():
    report = json.loads(payload_path.read_text(encoding="utf-8"))
    st.caption("Local cached-report validation · real local pipeline payload")
elif state == "abstention":
    report = _fixture(abstention=True)
    st.caption("Fixture-based abstention validation · not a real-video replay")
else:
    report = _fixture(benchmark=state == "benchmark")
    st.caption("Fixture-based benchmark rendering validation · not a real-video replay")

render_report(report, mode, {})
