"""Creator-facing Creator Memory views; no SQL or analysis logic lives here."""

from dataclasses import asdict
from html import escape

import streamlit as st

from ui.components import empty_state, section_heading
from ui.report import render_report


def _profile_form(service, profile=None):
    profile = profile or {}
    section_heading("Creator Profile", "Set up the local profile that saved analyses belong to.")
    with st.form("creator_memory_profile"):
        display_name = st.text_input("Display name", value=profile.get("display_name", ""))
        channel_name = st.text_input("Channel name", value=profile.get("channel_name", ""))
        channel_url = st.text_input("Channel URL (optional)", value=profile.get("channel_url") or "")
        external_id = st.text_input("External channel ID (optional)", value=profile.get("external_channel_id") or "")
        niche = st.text_input("Niche (optional, entered by you)", value=profile.get("niche") or "")
        submitted = st.form_submit_button("Save local profile", type="primary")
    if submitted:
        if not display_name.strip() or not channel_name.strip():
            st.warning("Add a display name and channel name to save this profile.")
        else:
            service.save_profile(display_name, channel_name, channel_url, external_id, niche)
            st.success("Creator Profile saved locally on this device.")
            st.rerun()


def _pattern_label(dimension, pattern):
    names = {
        "opening_strategy": "Opening strategy", "primary_visual_focus": "Visual focus",
        "progression_style": "Progression", "subject_timing": "Subject timing",
        "subject_presence": "Subject presence", "multiple_subjects": "Multiple subjects",
        "written_information_state": "Written information", "recommendation_state": "Recommendation state",
    }
    state = pattern.get("state", "").replace("_", " ")
    value = str(pattern.get("value") if pattern.get("value") is not None else "More history needed").replace("_", " ")
    return f"<div class='stratify-card'><span class='stratify-label'>{escape(names.get(dimension, dimension))}</span><h3>{escape(value.title())}</h3><p>{escape(state.title())}</p></div>"


def render_current_comparison(comparison):
    state = comparison.get("state", "insufficient_history")
    labels = {
        "insufficient_history": "More history is needed",
        "matches_typical_pattern": "Matches your usual pattern",
        "partially_matches_history": "Partially matches your history",
        "differs_from_usual_pattern": "Different from your recent history",
        "newly_observed_pattern": "A newly observed pattern",
        "evidence_too_limited": "Evidence is too limited",
    }
    section_heading("Compared with your history", "Historical context for this report—not a performance prediction.")
    st.markdown(
        f"<div class='stratify-card memory-comparison-card'><span class='stratify-badge'>"
        f"{escape(labels.get(state, 'Historical comparison'))}</span>"
        f"<p style='margin-top:.85rem'>{escape(comparison.get('message', 'No supported historical comparison yet.'))}</p>"
        "<p class='stratify-muted'>This describes repeated creative structure; it does not imply better performance or audience preference.</p></div>",
        unsafe_allow_html=True,
    )


def render_save_controls(service, report, project, product_mode):
    profile = service.profile()
    if not profile:
        st.info("Create a Creator Memory profile to save this report. You can continue analyzing without one.")
        return
    if service.dashboard()["counts"]["analyses"]:
        comparison = service.comparison(report)
        render_current_comparison(comparison)
    if st.button("Save this analysis to Creator Memory", type="primary", width="stretch"):
        try:
            saved = service.save_report(report, project)
            st.success("Analysis saved locally to Creator Memory.")
            st.session_state["creator_memory_saved_analysis_id"] = saved["analysis_id"]
        except Exception as exc:
            st.warning("The report is ready, but it could not be saved to Creator Memory. Try again in a moment.")
            if product_mode == "builder":
                st.error(f"Persistence error: {exc}")


def _dashboard(service, data, product_mode):
    profile, counts, memory = data["profile"], data["counts"], data["memory"]
    st.markdown(
        f"<section class='stratify-hero platform-hero'><div class='stratify-eyebrow'>Creator Memory</div>"
        f"<h1 style='font-size:clamp(2.25rem,5vw,4rem);overflow-wrap:anywhere'>{escape(profile['display_name'])}</h1>"
        f"<p>{escape(profile['channel_name'])} · Saved locally on this device</p></section>",
        unsafe_allow_html=True,
    )
    a, b, c = st.columns(3)
    a.metric("Saved videos", counts["videos"])
    b.metric("Saved analyses", counts["analyses"])
    c.metric("Memory confidence", memory["confidence"].replace("_", " ").title())
    if not counts["analyses"]:
        empty_state("Your first saved report establishes a baseline", "Creator Memory becomes useful as you save analyses.")
    elif counts["analyses"] == 1:
        st.info("One analysis is history, not yet a recurring pattern. Save another report to begin comparing structure.")
    if counts["analyses"]:
        section_heading("Your usual opening patterns", "Repeated observations across saved analyses, with small samples treated conservatively.")
        st.markdown("<div class='stratify-grid'>" + "".join(
            _pattern_label(key, value) for key, value in memory["patterns"].items()
        ) + "</div>", unsafe_allow_html=True)
    if memory["date_range"]:
        st.caption(f"Saved history: {memory['date_range']['start'][:10]} to {memory['date_range']['end'][:10]}")
    if data["errors"]:
        st.warning("One saved analysis could not be read and was skipped. Other history remains available.")


def _fallback_saved_report(result, product_mode):
    historical = result.get("historical") or {}
    st.warning(result.get("message") or "Only a partial saved summary is available.")
    summary = result.get("normalized_summary") or {}
    if summary:
        st.markdown(
            "<div class='stratify-card'><h3>Available historical summary</h3>" +
            "".join(
                f"<p><strong>{escape(key.replace('_', ' ').title())}:</strong> "
                f"{escape(str(value).replace('_', ' '))}</p>"
                for key, value in summary.items()
                if value is not None and value != "" and value != []
            ) + "</div>",
            unsafe_allow_html=True,
        )
    for detail in result.get("unavailable_details") or []:
        st.info(detail)
    if historical:
        st.caption(
            f"Saved analysis · {str(historical.get('analysis_date') or '')[:10]} · "
            f"Revision {historical.get('revision') or 1}"
        )
    if product_mode == "builder":
        with st.expander("Builder reconstruction diagnostics"):
            st.json(result.get("diagnostics") or {})


def _render_reopened(service, analysis_id, product_mode, version_metadata):
    result = service.reopen_analysis(analysis_id)
    if st.button("Back to saved history", key="close_saved_analysis"):
        st.session_state.pop("creator_memory_open_analysis", None)
        st.rerun()
    if result.get("status") != "reconstructed":
        _fallback_saved_report(result, product_mode)
        return
    saved = result["report"].get("saved_history") or {}
    title = (result["report"].get("video") or {}).get("title") or "Saved historical analysis"
    st.markdown(
        f"<div class='stratify-card'><span class='stratify-badge'>Saved historical analysis</span>"
        f"<h2>{escape(title)}</h2><p>Originally analyzed {escape(str(saved.get('analysis_date') or '')[:10])} "
        f"· Revision {escape(str(saved.get('revision') or 1))}</p>"
        "<p class='stratify-muted'>Opening this report did not reacquire the video or rerun analysis.</p></div>",
        unsafe_allow_html=True,
    )
    render_report(result["report"], product_mode, version_metadata)
    if product_mode == "builder":
        with st.expander("Builder reconstruction diagnostics"):
            st.json(result.get("diagnostics") or {})


def _history(service, data, product_mode, version_metadata):
    section_heading("Analysis history", "One card per video, with analysis revisions kept together.")
    selected = st.session_state.get("creator_memory_open_analysis")
    if selected:
        _render_reopened(service, selected, product_mode, version_metadata)
        return
    if not data["history"]:
        empty_state("No saved history yet", "Save a completed report when you want it to contribute to Creator Memory.")
        return
    for item in data["history"]:
        label = item.get("title") or "Untitled video project"
        with st.expander(f"{label} · {item['revision_count']} revision(s)", expanded=False):
            st.write({
                "Analyzed": (item.get("latest_analysis_at") or item.get("analyzed_at") or "")[:10],
                "Opening strategy": (item.get("opening_strategy") or "Not available").replace("_", " "),
                "Primary visual focus": (item.get("primary_visual_focus") or "Not available").replace("_", " "),
                "Recommendation": (item.get("recommendation_state") or "Not available").replace("_", " "),
                "Experiments": item["experiment_count"],
                "Confidence / completeness": item.get("recommendation_confidence") or item.get("analysis_completeness") or "Limited",
            })
            for revision in item.get("revisions") or []:
                label = (
                    f"Open saved report · Revision {revision['revision']} · "
                    f"{str(revision.get('created_at') or '')[:10]}"
                )
                if st.button(label, key=f"open_analysis_{revision['id']}"):
                    st.session_state["creator_memory_open_analysis"] = revision["id"]
                    st.rerun()
            confirm = st.checkbox("I understand this removes this project's saved analyses and experiments.", key=f"confirm_project_{item['id']}")
            if st.button("Delete this saved project", key=f"delete_project_{item['id']}", disabled=not confirm):
                service.delete_project(item["id"])
                st.rerun()


def _experiments(service, data):
    section_heading("Experiment tracking", "Status and outcome notes are always entered by you.")
    if not data["experiments"]:
        empty_state("No saved experiments", "Experiments generated with a saved analysis will appear here.")
        return
    groups = ("suggested", "planned", "running", "completed", "rejected", "archived")
    for status in groups:
        items = [item for item in data["experiments"] if item.status == status]
        if not items:
            continue
        st.subheader(status.title())
        for item in items:
            with st.expander(item.dimension.replace("_", " ").title()):
                st.write(item.hypothesis or item.change_description)
                next_status = st.selectbox("Status", groups, index=groups.index(item.status), key=f"status_{item.id}")
                notes = st.text_area("Creator notes", value=item.creator_notes, key=f"notes_{item.id}")
                result = st.text_area("Result summary (user-entered)", value=item.result_summary, key=f"result_{item.id}")
                if st.button("Update experiment", key=f"update_{item.id}"):
                    service.update_experiment(item.id, status=next_status, creator_notes=notes, result_summary=result)
                    st.success("Experiment updated.")
                    st.rerun()


def _data_management(service):
    section_heading("Local data", "Creator Memory stays on this device; cloud synchronization is not included.")
    st.info("The database stores analysis records and notes, not videos, extracted frames, secrets, or cache files. Deleting the local database removes saved memory. Storage is not claimed to be encrypted.")
    try:
        export = service.export_json()
        st.download_button("Export Creator Memory (JSON)", export, "stratify_creator_memory.json", "application/json")
    except ValueError:
        pass
    confirm = st.checkbox("I understand this permanently resets all local Creator Memory.", key="confirm_memory_reset")
    if st.button("Reset all local Creator Memory", disabled=not confirm):
        service.reset()
        st.success("Local Creator Memory was reset.")
        st.rerun()


def render_memory_workspace(service, product_mode, access, version_metadata=None):
    if access.creator_memory == "disabled":
        st.info("Creator Memory is currently disabled.")
        return
    if access.creator_memory == "preview":
        st.markdown("## Creator Memory preview")
        st.info("Creator Memory will organize saved analyses, recurring patterns, history comparisons, and experiments. No history is invented in preview mode.")
        return
    profile = service.profile()
    if not profile:
        st.markdown("## Creator Memory")
        st.info("Creator Memory becomes useful as you save analyses. Your first saved report establishes a baseline.")
        _profile_form(service)
        return
    data = service.dashboard()
    tabs = st.tabs(["Overview", "History", "Experiments", "Profile & data"])
    with tabs[0]:
        _dashboard(service, data, product_mode)
    with tabs[1]:
        _history(service, data, product_mode, version_metadata or {})
    with tabs[2]:
        _experiments(service, data)
    with tabs[3]:
        _profile_form(service, profile)
        _data_management(service)
    if product_mode == "builder":
        with st.expander("Builder diagnostics: Creator Memory"):
            st.json(service.diagnostics)
