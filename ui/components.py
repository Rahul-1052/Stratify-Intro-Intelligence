from html import escape

import streamlit as st


PROGRESS_STAGES = (
    "Acquiring intro",
    "Observing visuals",
    "Understanding the opening",
    "Finding comparable videos",
    "Qualifying benchmarks",
    "Comparing evidence",
    "Building experiments",
)


def clean_value(value):
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"", "none", "null", "unknown", "unavailable", "n/a"}:
        return ""
    return text


def safe(value):
    return escape(clean_value(value))


def confidence_badge(confidence):
    label = clean_value(confidence) or "Low"
    return f'<span class="stratify-badge">{escape(label.title())} confidence</span>'


def section_heading(title, description=""):
    st.header(title)
    if description:
        st.markdown(
            f'<p class="stratify-section-note">{escape(description)}</p>',
            unsafe_allow_html=True,
        )


def empty_state(title, message):
    st.markdown(
        f"""
        <div class="stratify-empty">
            <h3>{escape(title)}</h3>
            <p class="stratify-muted">{escape(message)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_card(title, value, eyebrow=""):
    eyebrow_html = (
        f'<div class="stratify-label">{escape(eyebrow)}</div>' if eyebrow else ""
    )
    return (
        '<div class="stratify-card">'
        f"{eyebrow_html}<h3>{escape(title)}</h3>"
        f"<p>{escape(value)}</p>"
        "</div>"
    )


def render_card_grid(cards, columns=3):
    if not cards:
        return
    class_name = "stratify-grid two" if columns == 2 else "stratify-grid"
    st.markdown(
        f'<div class="{class_name}">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


class ProgressPresenter:
    def __init__(self):
        self.current = 0
        self.placeholder = st.empty()
        self.render()

    def update(self, message):
        message_text = str(message or "").lower()
        matches = (
            (0, ("acquir", "download", "video context", "metadata")),
            (1, ("watch", "observ", "visual", "frame")),
            (2, ("understand", "creator decision", "content")),
            (3, ("discover", "search", "shortlist", "benchmark context")),
            (4, ("qualif", "viewer job", "compatib")),
            (5, ("learn", "compar", "reason", "pattern")),
            (6, ("experiment", "recommend", "report")),
        )
        for index, keywords in matches:
            if any(keyword in message_text for keyword in keywords):
                self.current = max(self.current, index)
                break
        self.render()

    def complete(self):
        self.current = len(PROGRESS_STAGES)
        self.render()

    def render(self):
        rows = []
        for index, label in enumerate(PROGRESS_STAGES):
            if index < self.current:
                state = "done"
            elif index == self.current and self.current < len(PROGRESS_STAGES):
                state = "active"
            else:
                state = "pending"
            rows.append(
                '<div class="stratify-progress-row '
                f'{state}"><span class="stratify-progress-dot"></span>'
                f"<span>{escape(label)}</span></div>"
            )
        self.placeholder.markdown(
            f'<div class="stratify-progress">{"".join(rows)}</div>',
            unsafe_allow_html=True,
        )
