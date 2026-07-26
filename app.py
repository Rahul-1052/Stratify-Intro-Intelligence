import os
import uuid
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

from stratify_platform.module_registry import run_module
from stratify_platform.projects import create_project, restore_project
from ui.components import ProgressPresenter
from ui.report import render_report
from ui.memory import render_memory_workspace, render_save_controls
from core.memory import CreatorMemoryService
from core.product_access import access_for_mode
from core.creator_report import build_creator_report
from core.creator_presentation import creator_confidence_presentation, creator_status_message
from ui.theme import apply_theme
from ui.workspace import (
    render_module_cards,
    render_platform_header,
    render_project_header,
    render_project_navigation,
    render_workspace_intro,
)
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


def valid_video_url(value):
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def render_landing():
    render_workspace_intro()

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
        try:
            report = run_module(
                "intro_intelligence",
                url=url.strip(), intro_seconds=15, frame_fps=1,
                progress_callback=progress.update,
                uploaded_video_path=uploaded_video_path,
            )
        except Exception as exc:
            report = {"status": "failed", "stage": "analysis_exception",
                      "warnings": [str(exc)] if DEBUG else [],
                      "error": str(exc) if DEBUG else "The analysis could not be completed."}

        if report.get("status") == "failed":
            status.update(
                label="Stratify could not build this report",
                state="error",
                expanded=True,
            )
            return report

        progress.complete()
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


def render_warnings(report, product_mode="creator"):
    creator = report.get("creator_report") or build_creator_report(report, product_mode=product_mode)
    presentation = creator_confidence_presentation(report, creator)
    warnings = report.get("warnings", []) or []
    message = creator_status_message(
        presentation, bool((creator.get("biggest_opportunity") or {}).get("supported"))
    )
    if presentation["analysis_status"]["value"] in {"Partial", "Failed"}:
        st.warning(message)
    elif presentation["analysis_status"]["value"] == "Completed with limited evidence":
        st.info(message)
    else:
        st.success(message)
    if has_youtube_download_block(warnings):
        st.info("Automatic video access was unavailable. Upload the video or its opening clip to complete the visual review.")
    if product_mode == "builder":
        with st.expander("Builder diagnostics", expanded=False):
            for warning in warnings:
                st.markdown(f"- {warning}")


def render_failure_state(report, product_mode="creator"):
    stage = report.get("stage", "analysis_failed")
    title = "This opening could not be analyzed"
    message = "No report was saved. Check the link or upload the opening clip and try again."
    if stage in {"normalize_url_failed", "invalid_url"}:
        title, message = "That video link is not valid", "Paste a complete video URL, or upload the opening clip instead."
    elif has_youtube_download_block(report.get("warnings", [])):
        title, message = "Automatic video access was unavailable", "Upload the video or its opening clip to continue with visual analysis."
    st.error(title)
    st.info(message)
    if product_mode == "builder" and report.get("error"):
        with st.expander("Builder diagnostics", expanded=False):
            st.write({"stage": stage, "error": report.get("error"), "warnings": report.get("warnings", [])})


st.set_page_config(page_title="Stratify", page_icon="S", layout="wide")
apply_theme()
memory_service = None
memory_error = None
try:
    memory_service = CreatorMemoryService()
except Exception as exc:
    memory_error = exc
project = restore_project(st.session_state.get("stratify_project"))
render_platform_header(project)
workspace_area = st.sidebar.radio("Workspace", ("Analyze", "Creator Memory"))

if workspace_area == "Creator Memory":
    if memory_service:
        render_memory_workspace(
            memory_service, ACTIVE_PRODUCT_MODE,
            access_for_mode(ACTIVE_PRODUCT_MODE), VERSION_METADATA,
        )
    else:
        st.warning("Creator Memory is temporarily unavailable. Your one-off analysis workspace is unaffected.")
        if ACTIVE_PRODUCT_MODE == "builder":
            st.error(f"Creator Memory initialization error: {memory_error}")
    st.stop()

if project and project.module_results.get("intro_intelligence"):
    render_project_header(project)
    render_project_navigation("intro_intelligence")
    render_module_cards(compact=True)
    report = project.module_results["intro_intelligence"]
    render_warnings(report, ACTIVE_PRODUCT_MODE)
    memory_callback = None
    if memory_service and access_for_mode(ACTIVE_PRODUCT_MODE).creator_memory == "enabled":
        memory_callback = lambda: render_save_controls(
            memory_service, report, project, ACTIVE_PRODUCT_MODE
        )
    render_report(
        report, ACTIVE_PRODUCT_MODE, VERSION_METADATA,
        after_opportunity=memory_callback,
    )
    if st.button("Start a new project", width="stretch"):
        st.session_state.pop("stratify_project", None)
        st.session_state.pop("creator_memory_saved_analysis_id", None)
        st.rerun()
else:
    url, uploaded_video, analyze_clicked = render_landing()
    render_module_cards()

    if analyze_clicked:
        if not url.strip() and uploaded_video is None:
            st.warning("Paste a video URL or upload an opening clip to begin.")
            st.stop()
        if url.strip() and not valid_video_url(url):
            st.warning("Paste a complete video URL, including https://, or upload the opening clip instead.")
            st.stop()

        project = create_project(
            source_url=url,
            upload_name=getattr(uploaded_video, "name", "") if uploaded_video else "",
            title="Video project",
        )
        project.module_run_statuses["intro_intelligence"] = "running"
        st.session_state["stratify_project"] = project.to_session()
        report = build_report(url, uploaded_video)
        if report.get("status") == "failed":
            project.module_run_statuses["intro_intelligence"] = "failed"
            st.session_state["stratify_project"] = project.to_session()
            render_failure_state(report, ACTIVE_PRODUCT_MODE)
            st.stop()

        project.title = report.get("video", {}).get("title") or project.title
        project.record_result("intro_intelligence", report)
        st.session_state["stratify_project"] = project.to_session()
        st.rerun()
