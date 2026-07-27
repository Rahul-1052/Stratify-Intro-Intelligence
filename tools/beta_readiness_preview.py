"""Deterministic Streamlit harness for private-beta UI validation."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from core.beta import BetaService, BetaStore
from core.product_validation.fixtures import fixture_cases
from ui.beta import render_beta_dashboard
from ui.report import render_report
from ui.theme import apply_theme


os.environ.setdefault("STRATIFY_BETA_ROOT", ".stratify_beta_preview")
store = BetaStore(os.environ["STRATIFY_BETA_ROOT"])
service = BetaService(store)


def seed_populated():
    if not store.list("feedback"):
        service.submit_feedback(
            "fixture-report", "fixture", "experiment",
            {
                "usefulness": 5, "most_useful_section": "Primary Experiment",
                "confusing": "The benchmark median wording was confusing.",
                "try_experiment": "Yes", "use_before_next_upload": "Yes",
                "would_pay": "Yes", "price_range": "$10–$24/month",
                "free_text": "I wanted clearer experiment timing.",
            },
            session_id="fixture-session",
        )
    if not store.list("analytics"):
        service.track("analysis_completed", "fixture-session", "fixture-report",
                      "fixture", {"validation_warning_count": 1})
        service.track("report_viewed", "fixture-session", "fixture-report", "fixture")
    if not store.list("reviews"):
        service.save_review("strong-visual", "fixture-reviewer", {
            "strongest_insight_usefulness": 5, "evidence_specificity": 4,
            "experiment_actionability": 5, "trustworthiness": 4,
            "clarity": 4, "novelty": 3, "generic_language_present": False,
            "recommendation_sensible": True, "contradiction_present": False,
            "report_worth_revisiting": True, "reviewer_notes": "Fixture review.",
        })
    if not store.list("testers"):
        service.upsert_tester({
            "tester_id": "fixture-tester", "display_name": "Tester Alpha",
            "invite_status": "active", "reports_generated": 1,
            "feedback_submitted": 1, "follow_up_status": "pending",
        })


st.set_page_config(page_title="Private Beta QA", layout="wide")
apply_theme()
view = st.query_params.get("view", "creator")
st.caption("Fixture-based private-beta UI validation · not a real-video replay.")

if view == "creator":
    report = fixture_cases()[0]["report"]
    report["report_id"] = "beta-preview-report"
    render_report(report, "creator", {})
elif view == "dashboard-populated":
    seed_populated()
    render_beta_dashboard("builder", service=service, golden_summary={
        "run_id": "fixture-golden-run", "case_count": 30,
        "completed": 0, "skipped": 30, "failed": 0,
        "latest_regression_comparison": [],
    })
elif view == "dashboard-creator":
    render_beta_dashboard("creator", service=service)
else:
    render_beta_dashboard("builder", service=service, golden_summary={})
