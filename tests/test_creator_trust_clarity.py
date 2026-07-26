import unittest
from contextlib import nullcontext
from unittest.mock import Mock, patch

from core.creator_presentation import (
    calibrate_experiments,
    creator_confidence_presentation,
)
from core.creator_report import build_creator_report
from tests.test_creator_product_readiness import semantic_report
from ui.memory import render_save_controls
from ui.report import render_report
from ui.workspace import render_module_cards


def creator_confidence(
    status="success", structural="high", recommendation="high",
    text="high", benchmark=False, supported=True, warnings=None,
):
    report = {"status": status, "warnings": warnings or []}
    creator = {
        "opening_snapshot": {"summary": "A subject appears before the setting changes."},
        "whats_working": [], "experiments": [],
        "biggest_opportunity": {
            "supported": supported, "confidence": recommendation,
            "source": "Observation-backed", "structural_dimension": "visual_anchor",
        },
        "confidence_summary": {
            "analysis_completeness": "complete", "evidence_confidence": structural,
            "recommendation_confidence": recommendation, "text_evidence": text,
        },
        "evidence_validation": {"benchmark_supported": benchmark},
    }
    report["creator_report"] = creator
    return report, creator


class ConfidenceReconciliationTests(unittest.TestCase):
    def test_completed_full_evidence(self):
        report, creator = creator_confidence(benchmark=True)
        value = creator_confidence_presentation(report, creator)
        self.assertEqual(value["analysis_status"]["value"], "Completed")
        self.assertEqual(value["evidence_coverage"]["value"], "Strong")
        self.assertEqual(value["structural_confidence"]["value"], "High")
        self.assertEqual(value["recommendation_confidence"]["value"], "High")

    def test_completed_with_limited_text(self):
        report, creator = creator_confidence(text="limited")
        value = creator_confidence_presentation(report, creator)
        self.assertEqual(value["analysis_status"]["value"], "Completed with limited evidence")
        self.assertEqual(value["evidence_coverage"]["value"], "Moderate")
        self.assertIn("text-like", value["evidence_coverage"]["explanation"])

    def test_high_structure_without_benchmark_caps_recommendation(self):
        report, creator = creator_confidence(benchmark=False)
        value = creator_confidence_presentation(report, creator)
        self.assertEqual(value["structural_confidence"]["value"], "High")
        self.assertEqual(value["recommendation_confidence"]["value"], "Moderate")
        self.assertIn("no qualified benchmark", value["recommendation_confidence"]["explanation"])

    def test_no_supported_opportunity_and_contradictions(self):
        report, creator = creator_confidence(supported=False)
        value = creator_confidence_presentation(report, creator)
        self.assertEqual(value["recommendation_confidence"]["value"], "No supported recommendation")
        creator["biggest_opportunity"].update({"supported": True, "evidence_consistency": "mixed"})
        value = creator_confidence_presentation(report, creator)
        self.assertEqual(value["recommendation_confidence"]["value"], "Limited")

    def test_saved_report_confidence_uses_same_mapping(self):
        report, creator = creator_confidence(status="partial", text="limited")
        report["saved_history"] = {"revision": 2}
        value = creator_confidence_presentation(report, creator)
        self.assertEqual(value["analysis_status"]["value"], "Partial")


class TextExperimentSafetyTests(unittest.TestCase):
    TEXT_EXPERIMENT = {
        "title": "Change written information", "structural_dimension": "information_order",
    }
    VISUAL_EXPERIMENT = {
        "title": "Change visual anchor", "structural_dimension": "visual_anchor",
    }

    def test_confirmed_text_is_kept(self):
        kept, excluded = calibrate_experiments([self.TEXT_EXPERIMENT], "high")
        self.assertEqual(len(kept), 1)
        self.assertEqual(excluded, [])

    def test_limited_isolated_and_unknown_text_are_excluded(self):
        for state in ("limited", "isolated", "unknown"):
            with self.subTest(state=state):
                kept, excluded = calibrate_experiments(
                    [self.TEXT_EXPERIMENT, self.VISUAL_EXPERIMENT], state
                )
                self.assertEqual(kept, [self.VISUAL_EXPERIMENT])
                self.assertEqual(len(excluded), 1)

    def test_experiment_count_is_not_padded(self):
        kept, _ = calibrate_experiments(
            [self.VISUAL_EXPERIMENT, self.TEXT_EXPERIMENT], "limited"
        )
        self.assertEqual(len(kept), 1)

    def test_limited_text_remains_a_report_limitation(self):
        creator = build_creator_report(semantic_report(text=True))
        self.assertEqual(creator["confidence_summary"]["text_evidence"], "limited")
        self.assertIn("text-like", creator["confidence_summary"]["plain_language"])


class CreatorRenderingClarityTests(unittest.TestCase):
    @patch("ui.report.render_card_grid")
    @patch("ui.report.empty_state")
    @patch("ui.report.st.markdown")
    @patch("ui.report.section_heading")
    def test_creator_terminology_removes_viewer_and_completeness_language(
        self, heading, markdown, empty, grid,
    ):
        report, creator = creator_confidence(text="limited", recommendation="moderate")
        render_report(report, "creator", {})
        rendered = " ".join(call.args[0] for call in markdown.call_args_list)
        self.assertNotIn("First viewer experience", rendered)
        self.assertIn("How the opening begins", rendered)
        self.assertNotIn("Analysis completeness", rendered)
        self.assertIn("Analysis status", rendered)
        self.assertIn("Structural interpretation", rendered)

    def test_snapshot_opportunity_and_support_are_distinct(self):
        repeated = "The opening uses one long repeated Creative Understanding sentence."
        creative = {
            "opening_snapshot": repeated, "timeline": [], "strengths": [],
            "status": "success", "semantic_confidence": "high",
            "priority": None,
            "experiments": [{
                "title": "Test one anchor", "structural_dimension": "visual_anchor",
                "current_structure": "multiple anchors", "alternative_structure": "one anchor",
                "observation": "Multiple anchors appear in the first phase.",
                "interpretation": repeated, "recommendation": "Hold one anchor first.",
                "reason": "This isolates visual hierarchy.", "what_stays_constant": "Everything else.",
                "confidence": "moderate", "limitations": ["No benchmark support."],
                "benchmark_supported": False, "source": "Observation-backed",
            }],
        }
        report = {
            "status": "success", "semantic_observation": {
                "text_evidence_confidence": "high",
            }, "benchmark": {}, "patterns": {},
        }
        creator = build_creator_report(report, creative)
        self.assertEqual(creator["opening_snapshot"]["summary"], repeated)
        self.assertNotEqual(creator["biggest_opportunity"]["summary"], repeated)
        self.assertNotEqual(creator["experiments"][0]["support"], repeated)


class WorkspaceAndMemoryCtaTests(unittest.TestCase):
    @patch("ui.workspace.st.expander", return_value=nullcontext())
    @patch("ui.workspace.st.markdown")
    def test_planned_modules_are_secondary(self, markdown, expander):
        available = Mock(is_available=True, description="Available")
        available.name = "Intro Intelligence"
        planned = Mock(is_available=False, description="Later")
        planned.name = "Story Intelligence"
        with patch("ui.workspace.list_modules", return_value=[available, planned]):
            render_module_cards()
        primary = markdown.call_args_list[0].args[0]
        secondary = markdown.call_args_list[1].args[0]
        self.assertIn("Intro Intelligence", primary)
        self.assertIn("Creator Memory", primary)
        self.assertNotIn("Story Intelligence", primary)
        self.assertIn("Story Intelligence", secondary)
        expander.assert_called_once_with("Coming later", expanded=False)

    @patch("ui.memory.st.markdown")
    def test_no_profile_cta_is_local_and_nonduplicative(self, markdown):
        service = Mock()
        service.profile.return_value = None
        render_save_controls(service, {}, Mock(), "creator")
        rendered = " ".join(call.args[0] for call in markdown.call_args_list)
        self.assertEqual(rendered.count("Save this analysis to Creator Memory"), 1)
        self.assertIn("stored locally", rendered)

    @patch("ui.memory.st.success")
    @patch("ui.memory.st.caption")
    @patch("ui.memory.st.button")
    def test_already_saved_state_has_no_duplicate_action(self, button, caption, success):
        service = Mock()
        service.profile.return_value = {"id": "creator"}
        service.dashboard.return_value = {"counts": {"analyses": 0}}
        with patch.dict("ui.memory.st.session_state", {"creator_memory_saved_analysis_id": "saved"}):
            render_save_controls(service, {}, Mock(), "creator")
        success.assert_called_once()
        button.assert_not_called()


if __name__ == "__main__":
    unittest.main()
