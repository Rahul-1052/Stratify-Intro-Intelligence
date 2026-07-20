import os
import uuid
from pathlib import Path

import streamlit as st

from core.stratify_report import run_stratify_report
from ui.components import ProgressPresenter
from ui.report import render_report
from ui.theme import apply_theme
from version import (
    BENCHMARK_ENGINE,
    INTRO_ENGINE,
    PATTERN_ENGINE,
    PRODUCT_MODE,
    RECOMMENDATION_ENGINE,
    STRATIFY_VERSION,
)


ACTIVE_PRODUCT_MODE = os.getenv("STRATIFY_PRODUCT_MODE", PRODUCT_MODE).strip().lower()
if ACTIVE_PRODUCT_MODE not in {"builder", "creator"}:
    ACTIVE_PRODUCT_MODE = "builder"

DEBUG = (
    ACTIVE_PRODUCT_MODE == "builder"
    and os.getenv("STRATIFY_DEBUG", "false").strip().lower() == "true"
)

TEMP_UPLOAD_DIR = Path("temp_uploads")
TEMP_UPLOAD_DIR.mkdir(exist_ok=True)

YOUTUBE_BLOCK_FALLBACK = (
    "YouTube blocked automatic intro access. Upload the video or its opening clip "
    "and rebuild the report for full visual analysis. Without an upload, Stratify "
    "will continue with the evidence it can access."
)

VERSION_METADATA = {
    "stratify_version": STRATIFY_VERSION,
    "intro_engine": INTRO_ENGINE,
    "pattern_engine": PATTERN_ENGINE,
    "benchmark_engine": BENCHMARK_ENGINE,
    "recommendation_engine": RECOMMENDATION_ENGINE,
    "debug": DEBUG,
}


def save_uploaded_video(uploaded_file):
    if uploaded_file is None:
        return None
    original_name = Path(uploaded_file.name or "uploaded_video.mp4")
    suffix = original_name.suffix.lower() or ".mp4"
    destination = TEMP_UPLOAD_DIR / f"upload_{uuid.uuid4().hex}{suffix}"
    with destination.open("wb") as output_file:
        output_file.write(uploaded_file.getbuffer())
    return str(destination)


def has_youtube_download_block(warnings):
    block_markers = (
        "yt_dlp_download_failed",
        "yt-dlp",
        "sign in to confirm you're not a bot",
        "sign in to confirm you’re not a bot",
        "youtube bot blocking",
        "http error 403",
        "forbidden",
    )
    warning_text = " ".join(str(warning).lower() for warning in warnings or [])
    return any(marker in warning_text for marker in block_markers)


def render_landing():
    st.markdown('<div class="stratify-brand">STRATIFY</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <section class="stratify-hero">
            <h1>See your opening clearly. Know what to test next.</h1>
            <p>Stratify turns direct intro observations into a practical creator report,
            then adds benchmark validation when reliable comparisons are available.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    left, center, right = st.columns([1, 6, 1])
    with center:
        url = st.text_input(
            "YouTube video URL",
            placeholder="Paste a YouTube video URL",
            label_visibility="collapsed",
        )
        analyze_clicked = st.button(
            "Analyze this intro",
            type="primary",
            width="stretch",
        )
        with st.expander("Upload fallback", expanded=False):
            st.caption(
                "If YouTube blocks access, upload the video or its opening clip. "
                "The URL still supplies metadata and comparison context."
            )
            uploaded_video = st.file_uploader(
                "Upload video or opening clip",
                type=["mp4", "mov", "mkv", "webm", "m4v"],
                label_visibility="collapsed",
            )
    return url, uploaded_video, analyze_clicked


def build_report(url, uploaded_video):
    uploaded_video_path = save_uploaded_video(uploaded_video)
    with st.status("Analyzing the opening", expanded=True) as status:
        progress = ProgressPresenter()
        report = run_stratify_report(
            url.strip(),
            intro_seconds=15,
            frame_fps=1,
            progress_callback=progress.update,
            uploaded_video_path=uploaded_video_path,
        )
        progress.complete()

        if report.get("status") == "failed":
            status.update(
                label="Stratify could not build this report",
                state="error",
                expanded=True,
            )
            return report

        status.update(
            label=(
                "Report ready with limited evidence"
                if report.get("status") == "partial"
                else "Report ready"
            ),
            state="complete",
            expanded=False,
        )
    return report


def render_warnings(report):
    warnings = report.get("warnings", []) or []
    if not warnings:
        return
    st.warning("Stratify built the best available report, but some evidence was unavailable.")
    with st.expander("What happened?", expanded=False):
        for warning in warnings:
            st.markdown(f"- {warning}")
        if has_youtube_download_block(warnings):
            st.info(YOUTUBE_BLOCK_FALLBACK)


st.set_page_config(page_title="Stratify", page_icon="S", layout="wide")
apply_theme()
url, uploaded_video, analyze_clicked = render_landing()

if analyze_clicked:
    if not url.strip():
        st.warning("Paste a YouTube URL to begin.")
        st.stop()

    report = build_report(url, uploaded_video)
    if report.get("status") == "failed":
        for warning in report.get("warnings", []) or []:
            st.error(warning)
        if has_youtube_download_block(report.get("warnings", [])):
            st.info(YOUTUBE_BLOCK_FALLBACK)
        st.stop()

    render_warnings(report)
    render_report(report, ACTIVE_PRODUCT_MODE, VERSION_METADATA)
