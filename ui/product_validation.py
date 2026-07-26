"""Builder-only Product Validation review board."""

from collections import Counter, defaultdict

import streamlit as st

from core.product_validation.checks import issue_signature
from core.product_validation.exports import export_bundle, summarize
from core.product_validation.models import ValidationScore
from core.product_validation.storage import ValidationStore


def _review(store, run, case):
    st.subheader("Case review")
    st.caption(f"{case.get('validation_kind')} · {case.get('niche')} · {case.get('source_type')}")
    st.write({"case": case.get("case_id"), "video": case.get("video_title") or case.get("source"),
              "analysis_status": case.get("analysis_status"), "reviewer_status": case.get("reviewer_status")})
    warnings = case.get("objective_warnings") or []
    st.markdown("### Objective warnings")
    st.caption("Automated heuristic review; warnings are not confirmed defects.")
    for item in warnings:
        st.warning(f"{item.get('section')}: {item.get('message')}")
    if case.get("pipeline_trace_reference"):
        trace = store.load_report(case["pipeline_trace_reference"])
        with st.expander("Pipeline trace diagnostics", expanded=False):
            st.write({"last_successful_stage": trace.get("last_successful_stage"),
                      "first_failed_stage": trace.get("first_failed_stage"),
                      "failure_category": trace.get("failure_category"),
                      "provenance": trace.get("provenance")})
            for stage in trace.get("stages", []):
                st.markdown(
                    f"**{stage.get('stage_name')}** · {stage.get('stage_status')} · "
                    f"{stage.get('duration_seconds', 0)}s"
                )
                if stage.get("evidence_counts"):
                    st.write(stage["evidence_counts"])
                if stage.get("warnings"):
                    st.caption(" · ".join(stage["warnings"]))
                if stage.get("error_message"):
                    st.error(f"{stage.get('error_type')}: {stage.get('error_message')}")
                if stage.get("output_references"):
                    st.caption("Outputs: " + ", ".join(stage["output_references"]))
    if case.get("report_reference"):
        from ui.report import render_report
        report = store.load_report(case["report_reference"])
        # Reuse the Creator renderer without recursively nesting Builder tools.
        render_report(report, "creator", {})
    st.markdown("### Human scorecard")
    with st.form(f"product_validation_review_{case.get('case_id')}"):
        score = {name: st.selectbox(name.replace("_", " ").title(), ("Awaiting human review", 1, 2, 3, 4, 5))
                 for name in ValidationScore.__dataclass_fields__}
        decision = st.selectbox("Decision", ("requires human review", "useful", "partially useful", "not useful", "abstention appropriate"))
        category = st.selectbox("Issue category", ("observation", "interpretation", "recommendation", "trust", "UX", "product", "acquisition", "evidence limitation", "infrastructure"))
        severity = st.selectbox("Issue severity", ("low", "medium", "high", "critical"))
        issue = st.text_input("Issue description")
        notes = st.text_area("Reviewer notes")
        one_change = st.text_area("If you could change only one thing, what would it be?")
        submitted = st.form_submit_button("Save review")
    if submitted:
        numeric = {key: (None if value == "Awaiting human review" else value) for key, value in score.items()}
        ValidationScore(**numeric).validate()
        review = {"case_id": case["case_id"], "reviewer_status": "reviewed", "score": numeric,
                  "decision": decision, "reviewer_notes": notes, "one_change": one_change, "issues": []}
        if issue.strip():
            review["issues"].append({"category": category, "severity": severity, "section": "report",
                                     "short_description": issue.strip(), "status": "requires human review"})
        store.save_review(run["run_id"], case["case_id"], review)
        st.success("Human review saved locally.")


def _hall(run):
    st.subheader("Hall of Failures")
    groups = defaultdict(list)
    for case in run.get("cases", []):
        for issue in case.get("issues", []):
            groups[issue_signature(issue)].append((case, issue))
    if not groups:
        st.info("No human-confirmed or classified failure entries are stored in this run.")
    for signature, items in groups.items():
        case, issue = items[0]
        with st.expander(f"{issue.get('severity', 'unknown').title()} · {issue.get('short_description')} · {len(items)} occurrence(s)"):
            st.write({"case": case.get("case_id"), "video": case.get("video_title") or case.get("source"),
                      "category": issue.get("category"), "section": issue.get("section"),
                      "supporting_evidence": issue.get("supporting_evidence"),
                      "status": issue.get("status"), "related_cases": [value[0].get("case_id") for value in items]})


def render_product_validation(product_mode="builder", store=None):
    if product_mode != "builder":
        return
    store = store or ValidationStore()
    st.header("Product Validation")
    st.caption("Local Builder workflow · automated warnings are heuristic · human review remains explicit.")
    runs = store.list_runs()
    if not runs:
        st.info("Run the fixture CLI or add a real-video manifest to begin.")
        return
    run = next(item for item in runs if item["run_id"] == st.selectbox("Validation run", [r["run_id"] for r in runs]))
    tabs = st.tabs(("Dashboard", "Case review", "Hall of Failures", "Exports"))
    with tabs[0]:
        summary = summarize(run)
        st.subheader("Validation run dashboard")
        st.write(summary)
        st.bar_chart(Counter(case.get("niche", "unknown") for case in run.get("cases", [])))
    with tabs[1]:
        cases = run.get("cases", [])
        if cases:
            identifiers = [case["case_id"] for case in cases]
            selected = st.selectbox("Validation case", identifiers, key="product_validation_case")
            index = identifiers.index(selected)
            def choose_case(case_id):
                st.session_state["product_validation_case"] = case_id
            previous, next_case = st.columns(2)
            previous.button("Previous case", disabled=index == 0, on_click=choose_case,
                            args=(identifiers[max(index - 1, 0)],))
            next_case.button("Next case", disabled=index == len(identifiers) - 1, on_click=choose_case,
                             args=(identifiers[min(index + 1, len(identifiers) - 1)],))
            _review(store, run, next(case for case in cases if case["case_id"] == selected))
    with tabs[2]:
        _hall(run)
    with tabs[3]:
        st.subheader("Export view")
        for name, content in export_bundle(run).items():
            st.download_button(f"Download {name}", content, file_name=name)
