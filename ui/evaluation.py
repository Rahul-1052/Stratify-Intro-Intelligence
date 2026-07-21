"""Hidden Builder-only evaluation dashboard."""

import json
from pathlib import Path

import streamlit as st

from core.evaluation.dataset import EvaluationDatasetStore
from core.evaluation.evaluation_runner import load_runs
from core.evaluation.exports import export_csv, export_json, export_markdown
from core.evaluation.report_comparison import compare_runs


DEFAULT_DATASET = Path("evaluation_data/dataset.json")
DEFAULT_OUTPUT = Path("evaluation_data")


def _rate_label(value):
    if not isinstance(value, dict) or value.get("rate") is None:
        return "Not measured"
    return f"{value['rate'] * 100:.1f}% ({value['numerator']}/{value['denominator']})"


def render_evaluation_dashboard(dataset_path=DEFAULT_DATASET, output_dir=DEFAULT_OUTPUT):
    dataset = EvaluationDatasetStore(dataset_path).load()
    runs = load_runs(output_dir)
    with st.expander("Internal Evaluation Framework", expanded=False):
        st.caption("Builder-only measurement. This data is never included in Creator Mode.")
        st.subheader("Dataset")
        st.write({"name": dataset["name"], "videos": len(dataset["videos"]), "completed": sum(video.status == "success" for video in dataset["videos"])})
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
