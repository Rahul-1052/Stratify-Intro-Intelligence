"""Deterministic visual QA surface for Product Validation V1."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from core.product_validation.fixtures import fixture_cases
from core.product_validation.runner import ProductValidationRunner
from core.product_validation.storage import ValidationStore
from ui.product_validation import render_product_validation
from ui.theme import apply_theme
from ui.workspace import render_platform_header

st.set_page_config(page_title="Product Validation fixture QA", layout="wide")
apply_theme()
render_platform_header()
st.caption("Fixture-based UI validation · not real-video pipeline validation · not human or creator review")
state = st.query_params.get("state", "builder")
if state == "creator":
    st.header("Creator report workspace")
    st.info("Product Validation controls are not available in Creator Mode.")
else:
    preview_root = Path(".stratify_validation") / "preview"
    store = ValidationStore(preview_root)
    if not store.list_runs():
        ProductValidationRunner(store).run(fixture_cases()[:10], run_id="fixture-preview",
            mode="fixture UI validation", no_network=True)
    preview_run = store.load_run("fixture-preview")
    if not preview_run["cases"][0].get("issues"):
        for case in preview_run["cases"][:2]:
            case["issues"] = [{"category": "trust", "severity": "medium",
                "section": "confidence", "short_description": "Fixture confidence wording needs review",
                "supporting_evidence": "Synthetic fixture issue for UI validation only.",
                "status": "requires human review"}]
    preview_run["cases"][7]["objective_warnings"] = [{
        "code": "conflicting_confidence", "severity": "warning", "section": "confidence",
        "message": "Fixture confidence labels require human reconciliation.",
        "classification": "automated heuristic review; requires human review"}]
    store.save_run(preview_run)
    render_product_validation("builder", store)
