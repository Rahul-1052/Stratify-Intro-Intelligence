"""Restrained platform and project shell for Streamlit."""

from html import escape

import streamlit as st

from stratify_platform.module_registry import list_modules


def render_platform_header(project=None):
    context = "Project workspace" if project else "Creative Intelligence Platform"
    st.markdown(
        '<div class="platform-topbar">'
        '<div><span class="platform-mark">STRATIFY</span>'
        f'<span class="platform-context">{escape(context)}</span></div>'
        '<span class="platform-version">Intro Intelligence &middot; Available now</span>'
        '</div>', unsafe_allow_html=True,
    )


def render_workspace_intro():
    st.markdown(
        '<section class="stratify-hero platform-hero">'
        '<div class="stratify-eyebrow">Creator workspace</div>'
        '<h1>Creative decisions, made visible.</h1>'
        '<p>Create a video project, run the intelligence modules available today, '
        'and keep every experiment grounded in observable evidence.</p>'
        '</section>', unsafe_allow_html=True,
    )


def render_module_cards(compact=False):
    modules = list_modules()
    available = [module for module in modules if module.is_available]
    planned = [module for module in modules if not module.is_available]
    cards = [
        '<div class="module-card"><span class="module-status available">Available now</span>'
        '<h3>Creator Memory</h3><p>Save analyses locally and compare future openings with your history.</p></div>'
    ]
    for module in available:
        cards.insert(0,
            '<div class="module-card">'
            '<span class="module-status available">Available now</span>'
            f'<h3>{escape(module.name)}</h3>'
            f'<p>{escape(module.description)}</p>'
            '</div>'
        )
    st.markdown(
        f'<div class="module-grid{" compact" if compact else ""}">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )
    if planned:
        with st.expander("Coming later", expanded=False):
            st.markdown(
                " · ".join(escape(module.name) for module in planned),
                unsafe_allow_html=True,
            )


def render_project_header(project):
    st.markdown(
        '<div class="project-header">'
        '<div class="stratify-eyebrow">Video project</div>'
        f'<h1>{escape(project.title)}</h1>'
        f'<p>{escape(project.source_type.replace("_", " ").title())} &middot; Intro Intelligence workspace</p>'
        '</div>', unsafe_allow_html=True,
    )


def render_project_navigation(active="intro_intelligence"):
    labels = (("overview", "Overview"), ("intro_intelligence", "Intro Intelligence"), ("experiments", "Experiments"))
    st.markdown(
        '<div class="project-nav">' + "".join(
            f'<span class="{"active" if key == active else ""}">{escape(label)}</span>'
            for key, label in labels
        ) + '</div>', unsafe_allow_html=True,
    )
