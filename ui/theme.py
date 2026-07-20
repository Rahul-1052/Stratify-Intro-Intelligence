import streamlit as st


THEME_CSS = """
<style>
:root {
    --stratify-ink: #111827;
    --stratify-muted: #667085;
    --stratify-border: #e7e9ee;
    --stratify-soft: #f7f8fa;
    --stratify-blue: #2563eb;
    --stratify-blue-dark: #1d4ed8;
}

.stApp {
    background: #fbfbfc;
    color: var(--stratify-ink);
}

[data-testid="stHeader"] {
    height: 0;
    visibility: hidden;
}

[data-testid="stAppDeployButton"],
[data-testid="stToolbar"],
[data-testid="stDecoration"] {
    display: none !important;
}

[data-testid="stMainBlockContainer"] {
    max-width: 1100px;
    padding-top: 3rem;
    padding-bottom: 6rem;
}

#MainMenu, footer { visibility: hidden; }

h1, h2, h3, p, label, button, input, textarea {
    font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

h1, h2, h3 {
    color: var(--stratify-ink);
    letter-spacing: -0.025em;
}

h2 {
    font-size: clamp(1.55rem, 3vw, 2rem) !important;
    margin-top: 3.5rem !important;
    margin-bottom: 1rem !important;
}

.stratify-brand {
    color: #344054;
    font-size: 0.76rem;
    font-weight: 750;
    letter-spacing: 0.18em;
    margin-bottom: 3.6rem;
    text-align: center;
}

.stratify-hero {
    margin: 0 auto 2.25rem;
    max-width: 820px;
    text-align: center;
}

.stratify-hero h1 {
    font-size: clamp(2.45rem, 6vw, 4.65rem);
    font-weight: 720;
    letter-spacing: -0.055em;
    line-height: 1.02;
    margin: 0;
}

.stratify-hero p {
    color: var(--stratify-muted);
    font-size: clamp(1rem, 2vw, 1.18rem);
    line-height: 1.7;
    margin: 1.4rem auto 0;
    max-width: 680px;
}

.stratify-input-wrap {
    margin: 0 auto;
    max-width: 780px;
}

[data-testid="stTextInput"] input {
    background: #fff;
    border: 1px solid #d9dde5;
    border-radius: 15px;
    box-shadow: 0 8px 28px rgba(16, 24, 40, 0.055);
    color: var(--stratify-ink);
    font-size: 1rem;
    min-height: 58px;
    padding: 0 1.1rem;
}

[data-testid="stTextInput"] input:focus {
    border-color: var(--stratify-blue);
    box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12);
}

.stButton > button[kind="primary"] {
    background: var(--stratify-blue);
    border: 1px solid var(--stratify-blue);
    border-radius: 14px;
    box-shadow: 0 8px 22px rgba(37, 99, 235, 0.2);
    color: #fff;
    font-size: 1rem;
    font-weight: 680;
    min-height: 54px;
    transition: background 120ms ease, box-shadow 120ms ease, transform 120ms ease;
}

.stButton > button[kind="primary"]:hover {
    background: var(--stratify-blue-dark);
    border-color: var(--stratify-blue-dark);
    box-shadow: 0 10px 26px rgba(37, 99, 235, 0.25);
    transform: translateY(-1px);
}

.stButton > button:focus-visible,
summary:focus-visible {
    outline: 3px solid rgba(37, 99, 235, 0.28) !important;
    outline-offset: 2px;
}

[data-testid="stExpander"] {
    background: rgba(255, 255, 255, 0.74);
    border: 1px solid var(--stratify-border);
    border-radius: 14px;
    box-shadow: none;
}

[data-testid="stExpander"] summary {
    min-height: 52px;
}

.stratify-upload {
    color: var(--stratify-muted);
    font-size: 0.88rem;
    margin: 1rem auto 0;
    max-width: 780px;
}

.stratify-report-head {
    border-top: 1px solid var(--stratify-border);
    margin-top: 4rem;
    padding-top: 2.25rem;
}

.stratify-eyebrow {
    color: var(--stratify-blue);
    font-size: 0.76rem;
    font-weight: 750;
    letter-spacing: 0.12em;
    margin-bottom: 0.55rem;
    text-transform: uppercase;
}

.stratify-card,
.stratify-hero-card {
    background: #fff;
    border: 1px solid var(--stratify-border);
    border-radius: 20px;
    box-shadow: 0 8px 26px rgba(16, 24, 40, 0.045);
}

.opportunity-card {
    background: linear-gradient(135deg, #ffffff 0%, #f4f7ff 100%);
    border-color: #dbe5ff;
}

.experiment-card {
    border-top: 3px solid #6d8ee8;
}

.experiment-card h3 {
    margin-top: 1rem;
}

.stratify-hero-card {
    padding: clamp(1.5rem, 4vw, 2.6rem);
}

.stratify-hero-card h2 {
    font-size: clamp(1.7rem, 4vw, 2.5rem) !important;
    line-height: 1.12;
    margin: 0.45rem 0 1rem !important;
}

.stratify-card {
    height: 100%;
    padding: 1.35rem;
}

.stratify-card h3 {
    font-size: 1rem;
    margin: 0 0 0.75rem;
}

.stratify-card p,
.stratify-hero-card p {
    color: #475467;
    line-height: 1.65;
    margin: 0.3rem 0;
}

.stratify-label {
    color: #667085;
    font-size: 0.72rem;
    font-weight: 720;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.stratify-badge {
    background: #eff6ff;
    border: 1px solid #dbeafe;
    border-radius: 999px;
    color: #1d4ed8;
    display: inline-block;
    font-size: 0.76rem;
    font-weight: 680;
    padding: 0.28rem 0.62rem;
}

.stratify-muted {
    color: var(--stratify-muted) !important;
}

.stratify-grid {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(3, minmax(0, 1fr));
}

.stratify-grid.two {
    grid-template-columns: repeat(2, minmax(0, 1fr));
}

.stratify-compare-grid {
    display: grid;
    gap: 0.75rem;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 1rem 0;
}

.stratify-compare-value {
    background: var(--stratify-soft);
    border-radius: 12px;
    padding: 0.8rem;
}

.stratify-compare-value strong {
    display: block;
    font-size: 0.93rem;
    margin-top: 0.28rem;
    overflow-wrap: anywhere;
}

.stratify-section-note {
    color: var(--stratify-muted);
    font-size: 0.96rem;
    line-height: 1.65;
    margin: -0.45rem 0 1.25rem;
    max-width: 760px;
}

.stratify-empty {
    background: #fff;
    border: 1px solid var(--stratify-border);
    border-radius: 18px;
    padding: 1.55rem;
}

.stratify-empty h3 {
    margin: 0 0 0.45rem;
}

.stratify-progress {
    display: grid;
    gap: 0.45rem;
    margin-top: 0.55rem;
}

.stratify-progress-row {
    align-items: center;
    color: #98a2b3;
    display: flex;
    font-size: 0.9rem;
    gap: 0.65rem;
}

.stratify-progress-dot {
    background: #d0d5dd;
    border-radius: 999px;
    height: 8px;
    width: 8px;
}

.stratify-progress-row.done { color: #475467; }
.stratify-progress-row.done .stratify-progress-dot { background: #7c9ee8; }
.stratify-progress-row.active { color: var(--stratify-ink); font-weight: 650; }
.stratify-progress-row.active .stratify-progress-dot {
    background: var(--stratify-blue);
    box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.11);
}

[data-testid="stAlert"] {
    border-radius: 14px;
}

@media (max-width: 760px) {
    [data-testid="stMainBlockContainer"] {
        padding-left: 1rem;
        padding-right: 1rem;
        padding-top: 1.25rem;
    }
    .stratify-brand { margin-bottom: 2.7rem; }
    .stratify-grid,
    .stratify-grid.two,
    .stratify-compare-grid { grid-template-columns: 1fr; }
    .stratify-hero-card { border-radius: 16px; }
}
</style>
"""


def apply_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)
