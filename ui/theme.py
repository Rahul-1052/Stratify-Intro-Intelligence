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

.platform-topbar {
    align-items: center;
    border-bottom: 1px solid var(--stratify-border);
    display: flex;
    justify-content: space-between;
    margin-bottom: 3.2rem;
    padding-bottom: 1rem;
}

.platform-mark {
    color: #344054;
    font-size: .76rem;
    font-weight: 780;
    letter-spacing: .18em;
}

.platform-context,
.platform-version {
    color: var(--stratify-muted);
    font-size: .78rem;
    margin-left: 1rem;
}

.platform-version {
    background: #eff6ff;
    border: 1px solid #dbeafe;
    border-radius: 999px;
    color: #1d4ed8;
    padding: .35rem .65rem;
}

.platform-hero { margin-bottom: 2rem; }

.module-grid {
    display: grid;
    gap: .9rem;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 2.25rem 0 3rem;
}

.module-grid.compact { margin-top: 1rem; }

.module-card {
    background: rgba(255,255,255,.82);
    border: 1px solid var(--stratify-border);
    border-radius: 16px;
    min-height: 160px;
    padding: 1.15rem;
}

.module-card h3 { font-size: 1rem; margin: .8rem 0 .45rem; }
.module-card p { color: var(--stratify-muted); font-size: .88rem; line-height: 1.55; }
.module-status { border-radius: 999px; display: inline-block; font-size: .7rem; font-weight: 720; padding: .25rem .52rem; }
.module-status.available { background: #ecfdf3; color: #027a48; }
.module-status.planned { background: #f2f4f7; color: #667085; }

.project-header h1 { font-size: clamp(2rem, 4vw, 3.25rem); margin: .3rem 0; }
.project-header p { color: var(--stratify-muted); }
.project-nav { border-bottom: 1px solid var(--stratify-border); display: flex; gap: .5rem; margin: 1.5rem 0; }
.project-nav span { color: var(--stratify-muted); font-size: .86rem; padding: .75rem .9rem; }
.project-nav span.active { border-bottom: 2px solid var(--stratify-blue); color: var(--stratify-ink); font-weight: 680; }

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

.abstention-card { background: #fff; border-color: var(--stratify-border); }
.opportunity-details, .version-pair, .confidence-grid {
    display: grid; gap: .8rem; grid-template-columns: repeat(2, minmax(0, 1fr)); margin: 1rem 0;
}
.opportunity-details p, .version-pair p { background: var(--stratify-soft); border-radius: 12px; padding: .8rem; }
.confidence-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.confidence-grid strong { display: block; margin-top: .35rem; text-transform: capitalize; }

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

.stratify-v4-hero {
    background: linear-gradient(145deg, #ffffff 0%, #f3f6ff 100%);
    border: 1px solid #dce5ff;
    border-radius: 24px;
    box-shadow: 0 18px 52px rgba(16, 24, 40, .08);
    padding: clamp(1.5rem, 5vw, 3rem);
}
.stratify-v4-hero h2 { font-size: clamp(1.65rem, 4vw, 2.55rem) !important; margin: .4rem 0 1.35rem !important; }
.stratify-v4-opportunity { border-left: 3px solid var(--stratify-blue); padding: .25rem 0 .25rem 1rem; }
.stratify-v4-opportunity span, .stratify-v4-metrics span,
.stratify-v4-experiment-grid span, .stratify-v4-confidence span,
.stratify-v4-benchmark span {
    color: var(--stratify-muted); display: block; font-size: .7rem;
    font-weight: 730; letter-spacing: .07em; text-transform: uppercase;
}
.stratify-v4-opportunity strong { display: block; font-size: 1.12rem; margin-top: .25rem; }
.stratify-v4-metrics {
    display: grid; gap: .65rem; grid-template-columns: repeat(5, minmax(0,1fr));
    margin-top: 1.5rem;
}
.stratify-v4-metrics > div, .stratify-v4-benchmark > div {
    background: rgba(255,255,255,.72); border: 1px solid var(--stratify-border);
    border-radius: 13px; min-width: 0; padding: .75rem;
}
.stratify-v4-metrics strong, .stratify-v4-benchmark strong {
    display: block; font-size: .86rem; margin-top: .28rem; overflow-wrap: anywhere;
}
.stratify-v4-timeline { border-left: 2px solid #dbe5ff; margin-left: 1.1rem; padding-left: 1.6rem; }
.stratify-v4-event {
    align-items: start; display: grid; gap: .8rem;
    grid-template-columns: 34px 50px minmax(0,1fr); margin: 0 0 1rem; position: relative;
}
.stratify-v4-event .event-icon, .stratify-v4-unavailable .event-icon {
    align-items: center; background: #eef4ff; border: 1px solid #d9e5ff; border-radius: 10px;
    color: #315bb5; display: flex; font-weight: 750; height: 34px; justify-content: center; width: 34px;
}
.stratify-v4-event .event-time { color: var(--stratify-muted); font-size: .8rem; font-weight: 680; padding-top: .45rem; }
.stratify-v4-event p { color: var(--stratify-muted); line-height: 1.5; margin: .18rem 0; }
.stratify-v4-finding, .stratify-v4-experiment, .stratify-v4-abstention {
    background: #fff; border: 1px solid #dce5ff; border-radius: 22px;
    box-shadow: 0 12px 38px rgba(16,24,40,.06); padding: clamp(1.4rem,4vw,2.3rem);
}
.stratify-v4-finding { border-left: 5px solid #5379d6; }
.stratify-v4-finding h3 { font-size: 1.35rem; margin: 1rem 0; }
.stratify-v4-finding p, .stratify-v4-abstention p { color: #475467; line-height: 1.65; }
.stratify-v4-experiment { background: linear-gradient(145deg,#fff 0%,#f7f9ff 100%); border-top: 4px solid #5379d6; }
.stratify-v4-experiment h2 { margin-top: 1rem !important; }
.stratify-v4-experiment-grid {
    display: grid; gap: .8rem; grid-template-columns: repeat(2,minmax(0,1fr));
}
.stratify-v4-experiment-grid > div {
    background: rgba(255,255,255,.78); border: 1px solid var(--stratify-border);
    border-radius: 13px; padding: .9rem;
}
.stratify-v4-experiment-grid p { color: #344054; line-height: 1.55; margin: .35rem 0 0; overflow-wrap: anywhere; }
.stratify-v4-abstention { border-color: #e4e7ec; }
.stratify-v4-confidence {
    display: grid; gap: 1rem; grid-template-columns: repeat(3,minmax(0,1fr));
}
.stratify-v4-confidence > div {
    background: #fff; border: 1px solid var(--stratify-border); border-radius: 18px; padding: 1.2rem;
}
.stratify-v4-confidence strong { display: block; font-size: 1.18rem; margin: .45rem 0; text-transform: capitalize; }
.stratify-v4-confidence p { color: var(--stratify-muted); line-height: 1.5; margin: 0; }
.stratify-v4-benchmark { display: grid; gap: .7rem; grid-template-columns: repeat(3,minmax(0,1fr)); }
.stratify-v4-unavailable {
    align-items: center; background: #fff; border: 1px solid var(--stratify-border);
    border-radius: 18px; display: flex; gap: 1rem; padding: 1.25rem;
}
.stratify-v4-unavailable h3, .stratify-v4-unavailable p { margin: .15rem 0; }
.stratify-v4-unavailable p { color: var(--stratify-muted); }
.stratify-v4-trust {
    background: #f8fafc; border: 1px solid var(--stratify-border); border-radius: 18px; padding: 1rem 1.2rem;
}
.stratify-v4-trust > div { align-items: start; display: flex; gap: .75rem; }
.stratify-v4-trust span { color: #2f855a; font-weight: 800; padding-top: .25rem; }
.stratify-v4-trust p { color: #475467; margin: .2rem 0; }

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
    .module-grid { grid-template-columns: 1fr; }
    .opportunity-details, .version-pair, .confidence-grid { grid-template-columns: 1fr; }
    .platform-version { display: none; }
    .stratify-hero-card { border-radius: 16px; }
    .stratify-v4-metrics, .stratify-v4-confidence,
    .stratify-v4-benchmark, .stratify-v4-experiment-grid { grid-template-columns: 1fr; }
    .stratify-v4-event { grid-template-columns: 34px 45px minmax(0,1fr); gap: .55rem; }
}

@media (prefers-color-scheme: dark) {
    .stratify-v4-hero, .stratify-v4-finding, .stratify-v4-experiment,
    .stratify-v4-abstention, .stratify-v4-confidence > div,
    .stratify-v4-unavailable, .stratify-v4-metrics > div,
    .stratify-v4-benchmark > div, .stratify-v4-experiment-grid > div {
        background: #151922;
        border-color: #303746;
    }
    .stratify-v4-hero { background: linear-gradient(145deg,#151922 0%,#18223a 100%); }
    .stratify-v4-experiment { background: linear-gradient(145deg,#151922 0%,#19233a 100%); }
    .stratify-v4-finding p, .stratify-v4-abstention p,
    .stratify-v4-experiment-grid p, .stratify-v4-trust p { color: #c9d1df; }
    .stratify-v4-trust { background: #111620; border-color: #303746; }
}
</style>
"""


def apply_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)
