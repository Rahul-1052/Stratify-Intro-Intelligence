import json
import unittest
from unittest.mock import patch

from core.creator_report import build_creator_report
from core.product_access import FREE_PREVIEW, access_for_mode
from ui.components import PROGRESS_STAGES
from ui.report import render_report


def semantic_report(frame_count=4, text=False, text_confidence="limited"):
    frames = [
        {"timestamp": index, "human_presence": True, "subject_count": 1,
         "scene_type": "person_focused", "visual_energy": "low",
         "text_overlay": text, "text_overlay_confidence": text_confidence}
        for index in range(frame_count)
    ]
    return {"status": "success", "vision": {"frame_observations": frames},
            "benchmark": {}, "patterns": {}}


class CreatorProductReadinessTests(unittest.TestCase):
    def test_neutral_strength_and_no_opportunity_are_successful_abstentions(self):
        creator = build_creator_report(semantic_report(frame_count=1))
        self.assertEqual(creator["strength_state"], "neutral")
        self.assertFalse(creator["biggest_opportunity"]["supported"])
        self.assertEqual(creator["biggest_opportunity"]["title"], "No supported structural change yet")
        self.assertEqual(creator["experiments"], [])

    def test_confidence_dimensions_are_separate_and_serializable(self):
        creator = build_creator_report(semantic_report(text=True))
        confidence = creator["confidence_summary"]
        self.assertEqual(set(confidence), {"analysis_completeness", "evidence_confidence", "recommendation_confidence", "text_evidence", "plain_language"})
        self.assertIn("text-like", confidence["plain_language"].lower())
        self.assertEqual(json.loads(json.dumps(creator))["report_version"], "creator-product-v1")

    def test_limited_text_never_claims_confirmed_written_information(self):
        creator = build_creator_report(semantic_report(text=True))
        snapshot = creator["opening_snapshot"]["summary"].lower()
        self.assertIn("possible written information", snapshot)
        self.assertNotIn("possible possible", snapshot)
        self.assertNotIn("written cues", snapshot)

    def test_experiment_contract_supports_zero_to_three(self):
        base = semantic_report()
        for count in range(4):
            items = [{
                "title": f"Test {index}", "suggested_test": f"Change {index}",
                "why_it_matters": "Qualified contrast.", "structural_dimension": f"dimension_{index}",
            } for index in range(count)]
            report = {**base, "benchmark": {"benchmark_quality": {"eligible_for_directional_learning": True}},
                      "patterns": {"top_creator_experiments": items}}
            creator = build_creator_report(report, creative_reasoning={
                "opening_snapshot": "A stable opening.", "timeline": [], "strengths": [],
                "experiments": [], "priority": None, "status": "success", "semantic_confidence": "moderate",
            })
            self.assertEqual(len(creator["experiments"]), count)
            for experiment in creator["experiments"]:
                self.assertTrue(experiment["hypothesis"] and experiment["change"])
                self.assertTrue(experiment["version_a"] and experiment["version_b"])
                self.assertTrue(experiment["what_stays_constant"] and experiment["limitation"])

    def test_access_boundaries_are_isolated_and_non_destructive(self):
        self.assertEqual(FREE_PREVIEW.visible_experiments, 1)
        self.assertFalse(FREE_PREVIEW.report_export)
        self.assertFalse(access_for_mode("creator").builder_diagnostics)
        self.assertTrue(access_for_mode("builder").builder_diagnostics)
        self.assertEqual(access_for_mode("creator").visible_experiments, 3)

    def test_loading_stages_use_creator_language(self):
        self.assertEqual(PROGRESS_STAGES, (
            "Preparing the opening", "Sampling key moments", "Observing visual changes",
            "Mapping the creative structure", "Comparing evidence", "Building experiments",
            "Preparing the report",
        ))

    @patch("ui.report.render_advanced_analysis")
    @patch("ui.report.render_card_grid")
    @patch("ui.report.st.markdown")
    @patch("ui.report.section_heading")
    def test_creator_builder_isolation(self, heading, markdown, grid, advanced):
        report = semantic_report()
        render_report(report, "creator", {})
        advanced.assert_not_called()
        render_report(report, "builder", {})
        advanced.assert_called_once()


if __name__ == "__main__":
    unittest.main()
