"""Creator feedback and Builder-only private-beta operations UI."""

import json
import os
import uuid
from pathlib import Path

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

from core.beta import BetaService, BetaStore
from core.beta.services import report_identifier


USEFUL_SECTIONS = (
    "Hero Summary", "Story of the Intro", "Strongest Finding",
    "Primary Experiment", "Confidence", "Benchmarks", "Supporting Evidence",
)


def _service():
    return BetaService(BetaStore(os.getenv("STRATIFY_BETA_ROOT", ".stratify_beta")))


def _session_id():
    return st.session_state.setdefault("stratify_beta_session_id", uuid.uuid4().hex)


def source_type(report):
    return str(
        (report.get("source_context") or {}).get("source_type")
        or (report.get("acquisition") or {}).get("source")
        or "unknown"
    )


def track_report_sections(report, product_mode):
    service = _service()
    report_id = report_identifier(report)
    key = f"beta_report_viewed_{report_id}_{product_mode}"
    if st.session_state.get(key):
        return
    common = {
        "session_id": _session_id(), "report_id": report_id,
        "source_type": source_type(report),
    }
    for event in (
        "report_viewed", "timeline_viewed", "strongest_finding_viewed",
        "primary_experiment_viewed", "benchmark_panel_viewed",
    ):
        service.safe_track(event, **common)
    if product_mode == "builder":
        service.safe_track("builder_mode_opened", **common)
    st.session_state[key] = True


def render_creator_feedback(report, product_mode="creator"):
    # Bare renderer unit tests have no Streamlit script context. Avoid creating
    # form state there; the actual app and AppTest both provide a context.
    if get_script_run_ctx(suppress_warning=True) is None:
        return
    track_report_sections(report, product_mode)
    report_id = report_identifier(report)
    submitted_key = f"stratify_feedback_submitted_{report_id}"
    st.markdown("### Help improve Stratify")
    st.caption("Optional · about one minute · saved only on this computer.")
    if st.session_state.get(submitted_key):
        st.success("Thanks—your feedback was saved for the private-beta review.")
        return
    with st.expander("Share feedback", expanded=False):
        with st.form(f"creator_feedback_{report_id}"):
            usefulness = st.radio(
                "How useful was this report?", (1, 2, 3, 4, 5),
                horizontal=True, index=None,
            )
            useful = st.selectbox(
                "Which section was most useful?", ("Choose one", *USEFUL_SECTIONS)
            )
            confusing = st.text_area(
                "Was anything confusing?",
                placeholder="Optional—tell us where the report lost you.",
            )
            try_experiment = st.radio(
                "Would you try the recommended experiment?",
                ("Yes", "No", "Not sure", "No experiment was recommended"),
                horizontal=True, index=None,
            )
            reuse = st.radio(
                "Would you use Stratify before your next upload?",
                ("Yes", "No", "Not sure"), horizontal=True, index=None,
            )
            would_pay = st.radio(
                "If Stratify stayed useful, would you consider paying for it?",
                ("Yes", "No", "Not sure"), horizontal=True, index=None,
            )
            price = st.selectbox(
                "Optional price range", ("Prefer not to say", "Under $10/month",
                "$10–$24/month", "$25–$49/month", "$50+/month"),
            )
            free_text = st.text_area(
                "Anything else you want us to know?", placeholder="Optional feedback"
            )
            submitted = st.form_submit_button("Submit feedback")
        if submitted:
            if usefulness is None:
                st.warning("Choose a usefulness rating before submitting.")
                return
            opportunity = (
                (report.get("creator_report") or {}).get("biggest_opportunity") or {}
            )
            answers = {
                "usefulness": usefulness,
                "most_useful_section": "" if useful == "Choose one" else useful,
                "confusing": confusing.strip(),
                "try_experiment": try_experiment,
                "use_before_next_upload": reuse,
                "would_pay": would_pay,
                "price_range": "" if price == "Prefer not to say" else price,
                "free_text": free_text.strip(),
            }
            service = _service()
            result = service.submit_feedback(
                report_id, source_type(report),
                "experiment" if opportunity.get("supported") else "abstention",
                answers, _session_id(),
            )
            if result["status"] in {"saved", "duplicate"}:
                st.session_state[submitted_key] = True
                service.safe_track(
                    "feedback_submitted", _session_id(), report_id,
                    source_type(report), {"recommendation_state": (
                        "experiment" if opportunity.get("supported") else "abstention"
                    )},
                )
                st.rerun()


def render_beta_dashboard(product_mode="builder", service=None, golden_summary=None):
    if product_mode != "builder":
        st.info("Private-beta operations are available only in Builder Mode.")
        return
    service = service or _service()
    st.title("Private Beta Review")
    st.caption(
        "Local operational data only. Small samples are directional and are not statistically significant."
    )
    if golden_summary is None:
        summaries = sorted(
            Path("validation/golden_dataset/runs").glob("*/summary.json"),
            key=lambda item: item.stat().st_mtime,
        )
        if summaries:
            try:
                latest = json.loads(summaries[-1].read_text(encoding="utf-8"))
                golden_summary = {
                    "run_id": latest.get("run_id"),
                    "case_count": len(latest.get("cases") or []),
                    "completed": sum(
                        item.get("status") == "completed"
                        for item in latest.get("cases") or []
                    ),
                    "skipped": sum(
                        item.get("status") == "skipped"
                        for item in latest.get("cases") or []
                    ),
                    "failed": sum(
                        item.get("status") == "failed"
                        for item in latest.get("cases") or []
                    ),
                    "latest_regression_comparison": latest.get("comparison") or [],
                }
            except (OSError, json.JSONDecodeError):
                golden_summary = {}
    summary = service.dashboard_summary(golden_summary)
    first = st.columns(4)
    first[0].metric("Reports generated", summary["total_reports_generated"])
    first[1].metric("Failed analyses", summary["failed_analyses"])
    first[2].metric("Feedback", summary["feedback_count"])
    first[3].metric(
        "Average usefulness",
        summary["average_usefulness"] if summary["average_usefulness"] is not None else "No data",
        help=f"Completed responses: n={summary['feedback_sample_size']}",
    )
    second = st.columns(4)
    second[0].metric("Repeat analyses", summary["repeat_analyses_by_session"])
    second[1].metric(
        "Experiment intent",
        f"{summary['experiment_intent_percentage']}%"
        if summary["experiment_intent_percentage"] is not None else "No data",
    )
    second[2].metric(
        "Next-upload intent",
        f"{summary['next_upload_reuse_intent']}%"
        if summary["next_upload_reuse_intent"] is not None else "No data",
    )
    second[3].metric("Willingness to pay", summary["willingness_to_pay_count"])
    tabs = st.tabs(("Feedback", "Quality scorecards", "Golden dataset", "Testers", "Exports"))
    with tabs[0]:
        st.subheader("Most useful sections")
        if summary["most_useful_sections"]:
            st.bar_chart(summary["most_useful_sections"])
        else:
            st.info("No completed creator feedback yet.")
        st.subheader("Common confusion themes")
        if summary["confusion_themes"]:
            st.dataframe(summary["confusion_themes"], hide_index=True, width="stretch")
        else:
            st.info("No confusion themes have been observed.")
    with tabs[1]:
        st.caption(f"Completed human reviews: n={summary['review_sample_size']}")
        if summary["review_averages"]:
            st.dataframe(
                [{"dimension": key.replace("_", " ").title(), "average": value}
                 for key, value in summary["review_averages"].items()],
                hide_index=True, width="stretch",
            )
        else:
            st.info("No completed report-quality scorecards yet.")
        with st.expander("Add report-quality scorecard", expanded=False):
            with st.form("beta_quality_scorecard"):
                case_id = st.text_input("Golden case ID or report ID")
                reviewer_id = st.text_input("Reviewer alias")
                score_options = ("Not scored", 1, 2, 3, 4, 5)
                scores = {
                    key: st.selectbox(
                        key.replace("_", " ").title(), score_options, key=f"score_{key}"
                    )
                    for key in (
                        "strongest_insight_usefulness", "evidence_specificity",
                        "experiment_actionability", "trustworthiness", "clarity", "novelty",
                    )
                }
                check_options = ("Not reviewed", "Yes", "No")
                checks = {
                    key: st.selectbox(
                        key.replace("_", " ").title(), check_options, key=f"check_{key}"
                    )
                    for key in (
                        "generic_language_present", "recommendation_sensible",
                        "contradiction_present", "report_worth_revisiting",
                    )
                }
                notes = st.text_area("Reviewer notes")
                save_review = st.form_submit_button("Save scorecard")
            if save_review:
                if not case_id.strip() or not reviewer_id.strip():
                    st.warning("Case ID and reviewer alias are required.")
                else:
                    values = {
                        key: None if value == "Not scored" else value
                        for key, value in scores.items()
                    }
                    values.update({
                        key: None if value == "Not reviewed" else value == "Yes"
                        for key, value in checks.items()
                    })
                    values["reviewer_notes"] = notes.strip()
                    review = service.save_review(case_id.strip(), reviewer_id.strip(), values)
                    st.success(
                        "Completed scorecard saved."
                        if review["completed"]
                        else "Draft scorecard saved; incomplete scores are excluded from averages."
                    )
    with tabs[2]:
        golden = summary.get("golden_dataset") or {}
        if golden:
            st.json(golden)
        else:
            st.info("Run the golden dataset CLI to populate regression status.")
        st.metric("Unresolved validation warnings", summary["unresolved_validation_warnings"])
    with tabs[3]:
        testers = service.store.list("testers")
        if testers:
            st.dataframe(testers, hide_index=True, width="stretch")
        else:
            st.info("No beta testers have been added.")
        upload = st.file_uploader("Import tester CSV", type=["csv"])
        if upload is not None and st.button("Import testers"):
            temporary = service.store.root / "testers" / "_import.csv"
            temporary.write_bytes(upload.getvalue())
            service.import_testers_csv(temporary)
            temporary.unlink(missing_ok=True)
            st.rerun()
    with tabs[4]:
        st.caption("Exports exclude raw video frames and report prose.")
        for collection in ("feedback", "analytics", "reviews", "testers"):
            if st.button(f"Export {collection} CSV", key=f"export_{collection}"):
                path = service.store.export_csv(collection)
                st.success(f"Saved {path}")
        if st.button("Export analytics summary CSV"):
            path = service.export_analytics_summary_csv(summary)
            st.success(f"Saved {path}")
        if st.button("Export beta review Markdown"):
            path = service.export_review_summary_markdown(summary)
            st.success(f"Saved {path}")
        with st.expander("Structured summary", expanded=False):
            st.code(json.dumps(summary, indent=2, sort_keys=True), language="json")
