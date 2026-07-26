"""Manual Streamlit verification of uploaded-file analysis without YouTube context."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from core.stratify_report import run_stratify_report
from ui.report import render_report
from ui.theme import apply_theme
from ui.workspace import render_platform_header

st.set_page_config(page_title="Local source validation", layout="wide")
apply_theme()
render_platform_header()
st.caption("Local uploaded-file compatibility validation · no YouTube metadata or network context")
path = os.getenv("STRATIFY_LOCAL_VALIDATION_PATH", "")
if not path:
    st.error("STRATIFY_LOCAL_VALIDATION_PATH is not configured.")
    st.stop()


@st.cache_data(show_spinner=False)
def analyze(local_path):
    return run_stratify_report(
        "", uploaded_video_path=local_path, local_source_type="uploaded_file",
        no_network=True,
    )


with st.spinner("Analyzing the supplied local video"):
    report = analyze(path)
if report.get("status") == "failed":
    st.error("Local uploaded-file analysis failed.")
    st.json(report)
else:
    st.success("Local uploaded-file analysis completed without YouTube context.")
    render_report(report, "creator", {})
