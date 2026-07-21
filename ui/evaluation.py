"""Hidden Builder-only evaluation dashboard."""

import json
from pathlib import Path

import streamlit as st

from core.evaluation.dataset import EvaluationDatasetStore
from core.evaluation.dataset_validation import (
    CONTROLLED_LABELS,
    REVIEW_STATES,
    dataset_readiness,
)
from core.evaluation.evaluation_runner import load_runs
from core.evaluation.exports import export_csv, export_json, export_markdown
from core.evaluation.report_comparison import compare_runs


DEFAULT_DATASET = Path("evaluation_data/dataset.json")
DEFAULT_OUTPUT = Path("evaluation_data")


def _rate_label(value):
    if not isinstance(value, dict) or value.get("rate") is None:
        return "Not measured"
    return f"{value['rate'] * 100:.1f}% ({value['numerator']}/{value['denominator']})"


LABELING_RULES = (
    "Judge only the opening interval analyzed by Stratify.",
    "Label visible and audible evidence, not the title's promise.",
    "Do not identify characters using metadata.",
    "Do not assume emotion, intent, story, retention, or audience psychology without evidence.",
    "A stable opening is not automatically weak.",
    "Text presence is not automatically a problem.",
    "Multiple subjects are not automatically confusing.",
    "No experiment is a valid answer.",
    "Mark uncertain evidence as uncertain instead of guessing.",
)


def _label(value):
    return str(value).replace("_", " ").title()


def _controlled_select(label, field, current, key):
    options = sorted(CONTROLLED_LABELS[field], key=lambda item: (item not in {"not_yet_reviewed", "uncertain", "unavailable"}, item))
    index = options.index(current) if current in options else 0
    return st.selectbox(label, options, index=index, format_func=_label, key=key)


def _render_readiness(dataset):
    readiness = dataset_readiness(dataset)
    st.subheader("Baseline V1 readiness")
    left, center, right = st.columns(3)
    left.metric("Reviewed", f"{readiness['completed_entries']}/{readiness['total_entries']}")
    center.metric("Completion", f"{readiness['completion_percentage']:.1f}%")
    right.metric("Baseline", "Ready" if readiness["baseline_v1_ready"] else "Not ready")
    st.progress(readiness["completion_percentage"] / 100 if readiness["total_entries"] else 0)
    st.write({
        "unreviewed": readiness["unreviewed_entries"],
        "incomplete": readiness["incomplete_entries"],
        "partial": readiness["partially_reviewed_entries"],
        "complete": readiness["completed_entries"],
        "category_balance": readiness["category_balance"],
    })
    if readiness["validation_errors"]:
        with st.expander("Dataset validation", expanded=False):
            for error in readiness["validation_errors"]:
                st.error(error)
    else:
        st.success("Dataset structure is valid. Baseline metrics remain unavailable until every review is complete.")
    return readiness


def _render_labeling_interface(store, dataset):
    videos = list(dataset.get("videos", []))
    if not videos:
        st.info("Add evaluation entries before beginning manual review.")
        return
    st.subheader("Manual opening review")
    identifiers = [video.evaluation_id or video.video_id for video in videos]
    current_id = st.session_state.get("evaluation_selected_id")
    if current_id not in identifiers:
        current_id = identifiers[0]
    selected_id = st.selectbox(
        "Dataset entry",
        identifiers,
        index=identifiers.index(current_id),
        format_func=lambda value: f"{value} · {videos[identifiers.index(value)].video_title}",
        key="evaluation_entry_selector",
    )
    st.session_state["evaluation_selected_id"] = selected_id
    index = identifiers.index(selected_id)
    video = videos[index]
    st.write({
        "evaluation_id": selected_id, "video_id": video.video_id,
        "category": video.category, "review_status": video.status,
        "opening_interval": f"0–{dataset.get('opening_interval_seconds', 15)} seconds",
    })
    st.caption(video.notes or "No selection note provided.")
    st.link_button("Open video externally", video.url)
    def move_to(identifier):
        st.session_state["evaluation_selected_id"] = identifier
        st.session_state["evaluation_entry_selector"] = identifier

    navigation = st.columns(2)
    navigation[0].button("Previous entry", disabled=index == 0, key="evaluation_previous", on_click=move_to, args=(identifiers[max(0, index - 1)],))
    navigation[1].button("Next entry", disabled=index == len(videos) - 1, key="evaluation_next", on_click=move_to, args=(identifiers[min(len(videos) - 1, index + 1)],))

    with st.expander("Manual labeling rules", expanded=True):
        for rule in LABELING_RULES:
            st.markdown(f"- {rule}")

    existing = dict(video.expected_manual_labels or {})
    with st.form("evaluation_manual_review"):
        st.caption("Leave fields as Not Yet Reviewed when the opening has not been judged. No value is inferred from metadata.")
        first, second = st.columns(2)
        with first:
            primary = _controlled_select("Primary visual focus", "primary_visual_focus", existing.get("primary_visual_focus", "not_yet_reviewed"), f"manual_primary_focus_{selected_id}")
            clarity = _controlled_select("Focus clarity", "focus_clarity", existing.get("focus_clarity", "not_yet_reviewed"), f"manual_focus_clarity_{selected_id}")
            opening = _controlled_select("Opening mode", "opening_mode", existing.get("opening_mode", "not_yet_reviewed"), f"manual_opening_mode_{selected_id}")
        with second:
            progression = _controlled_select("Visual progression", "visual_progression", existing.get("visual_progression", "not_yet_reviewed"), f"manual_visual_progression_{selected_id}")
            text_role = _controlled_select("Text role", "text_role", existing.get("text_role", "not_yet_reviewed"), f"manual_text_role_{selected_id}")
            confidence = _controlled_select("Manual confidence", "manual_confidence", existing.get("manual_confidence", "not_yet_reviewed"), f"manual_confidence_{selected_id}")
        beat_value = existing.get("number_of_semantic_beats")
        beat_count = st.number_input("Semantic beat count", min_value=0, step=1, value=beat_value if isinstance(beat_value, int) else None, placeholder="Not yet reviewed", key=f"manual_beats_{selected_id}")
        strength = st.text_input("Strongest observed quality", value=str(existing.get("best_strength", "")), placeholder="Visible evidence only; unavailable or uncertain is allowed", key=f"manual_strength_{selected_id}")
        weakness = st.text_input("Largest observed opportunity", value=str(existing.get("largest_weakness", "")), placeholder="A stable opening is not automatically weak", key=f"manual_weakness_{selected_id}")
        current_experiments = existing.get("expected_experiment")
        experiment_text = st.text_area("Acceptable experiment or experiments", value="\n".join(current_experiments) if isinstance(current_experiments, list) else str(current_experiments or ""), placeholder="One per line; leave blank unless reviewed", key=f"manual_experiments_{selected_id}")
        no_experiment = st.checkbox("Reviewed: no experiment is appropriate", value="expected_experiment" in existing and current_experiments == [], key=f"manual_no_experiment_{selected_id}")
        reviewer_notes = st.text_area("Reviewer notes", value=video.reviewer_notes or "", placeholder="Optional notes about uncertainty or evidence", key=f"manual_notes_{selected_id}")
        statuses = ["unreviewed", "incomplete", "partial", "complete"]
        review_status = st.selectbox("Review status", statuses, index=statuses.index(video.status) if video.status in statuses else 0, format_func=_label, key=f"manual_status_{selected_id}")
        saved = st.form_submit_button("Save manual review", type="primary")
    if saved:
        labels = {}
        values = {
            "primary_visual_focus": primary, "focus_clarity": clarity,
            "opening_mode": opening, "visual_progression": progression,
            "text_role": text_role, "manual_confidence": confidence,
        }
        labels.update({key: value for key, value in values.items() if value != "not_yet_reviewed"})
        if beat_count is not None:
            labels["number_of_semantic_beats"] = int(beat_count)
        if strength.strip():
            labels["best_strength"] = strength.strip()
        if weakness.strip():
            labels["largest_weakness"] = weakness.strip()
        experiments = [line.strip() for line in experiment_text.splitlines() if line.strip()]
        if no_experiment:
            labels["expected_experiment"] = []
        elif experiments:
            labels["expected_experiment"] = experiments
        try:
            store.save_manual_review(selected_id, labels, review_status, reviewer_notes)
            st.success("Manual review saved. No labels were generated automatically.")
        except (KeyError, ValueError) as exc:
            st.error(str(exc))


def render_evaluation_dashboard(dataset_path=DEFAULT_DATASET, output_dir=DEFAULT_OUTPUT):
    store = EvaluationDatasetStore(dataset_path)
    dataset = store.load()
    runs = load_runs(output_dir)
    with st.expander("Internal Evaluation Framework", expanded=False):
        st.caption("Builder-only measurement. This data is never included in Creator Mode.")
        st.subheader("Dataset")
        st.write({"name": dataset["name"], "videos": len(dataset["videos"]), "completed": sum(video.status == "complete" for video in dataset["videos"])})
        _render_readiness(dataset)
        _render_labeling_interface(store, dataset)
        if not runs:
            st.info("No evaluation runs are stored yet.")
            return
        latest = runs[0]
        metrics = latest.get("metrics", {})
        st.subheader("Latest evaluation")
        st.write({
            "run_id": latest.get("run_id"), "created_at": latest.get("created_at"),
            "observation_coverage": _rate_label(metrics.get("observation_coverage")),
            "semantic_coverage": _rate_label(metrics.get("semantic_coverage")),
            "manual_agreement": _rate_label(metrics.get("manual_agreement_rate")),
            "average_beats": metrics.get("average_beat_count"),
        })
        st.subheader("Agreement and category statistics")
        st.write(metrics.get("per_category_agreement", {}))
        st.subheader("Failures and common mistakes")
        st.write(latest.get("failure_analysis", {}))
        if len(runs) >= 2:
            st.subheader("Trend across evaluations")
            st.write(compare_runs(runs[1], runs[0]))
        st.subheader("Exports")
        st.download_button("Download evaluation JSON", export_json(latest), file_name=f"{latest.get('run_id')}.json", mime="application/json")
        st.download_button("Download evaluation CSV", export_csv(latest), file_name=f"{latest.get('run_id')}.csv", mime="text/csv")
        st.download_button("Download Markdown summary", export_markdown(latest), file_name=f"{latest.get('run_id')}.md", mime="text/markdown")
