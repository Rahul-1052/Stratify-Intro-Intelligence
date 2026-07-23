import unittest
from unittest.mock import patch

from core.creator_report import build_creator_report
from ui.report import render_report


def observed_report():
    return {
        "intro_observation": {"status": "success", "observation": {"opening_summary": "A person enters a bright workshop.", "hook_type": "visible action", "main_subject": "person building a device"}},
        "feature_report": {"feature_summary": {"pacing": "moderate", "text_overlay": "minimal"}},
        "vision": {"frame_observations": [
            {"timestamp": 0, "scene_type": "workshop", "visual_energy": "moderate", "human_presence": True},
            {"timestamp": 2, "scene_type": "workshop", "visual_energy": "high", "text_overlay": True},
        ]},
        "patterns": {}, "benchmark": {},
    }


class CreatorReportV1Tests(unittest.TestCase):
    def test_observation_only_always_has_customer_value_sections(self):
        creator = build_creator_report(observed_report())
        self.assertTrue(creator["opening_snapshot"]["summary"])
        self.assertTrue(creator["intro_timeline"])
        self.assertTrue(creator["whats_working"])
        self.assertGreaterEqual(len(creator["experiments"]), 1)
        self.assertTrue(all(not item["benchmark_supported"] for item in creator["experiments"]))
        self.assertTrue(all(item["observation"] and item["interpretation"] and item["recommendation"] and item["reason"] for item in creator["experiments"]))
        self.assertEqual(creator["evidence_validation"]["status"], "observation_only")

    def test_qualified_benchmark_is_optional_enrichment(self):
        report = observed_report()
        report["benchmark"] = {"benchmark_quality": {"eligible_for_directional_learning": True, "score": 82}}
        report["patterns"] = {"top_creator_experiments": [{"title": "Test earlier action", "suggested_test": "Move the observed action earlier.", "why_it_matters": "Three qualified intros supported this contrast."}]}
        creator = build_creator_report(report)
        self.assertGreaterEqual(len(creator["experiments"]), 1)
        self.assertTrue(creator["experiments"][0]["benchmark_supported"])
        self.assertEqual(creator["experiments"][0]["source"], "Benchmark-supported")
        self.assertEqual(creator["evidence_validation"]["status"], "validated")

    def test_unavailable_benchmark_never_claims_support(self):
        report = observed_report()
        report["benchmark"] = {"benchmark_quality": {"eligible_for_directional_learning": False}}
        report["patterns"] = {"top_creator_experiments": [{"title": "Unsupported benchmark claim"}]}
        creator = build_creator_report(report)
        self.assertGreaterEqual(len(creator["experiments"]), 1)
        self.assertFalse(any(item["benchmark_supported"] for item in creator["experiments"]))

    @patch("ui.report.render_advanced_analysis")
    @patch("ui.report.render_card_grid")
    @patch("ui.report.st.markdown")
    @patch("ui.report.section_heading")
    def test_report_renders_all_required_sections(self, heading, markdown, grid, advanced):
        report = observed_report()
        report["creator_report"] = build_creator_report(report)
        render_report(report, "creator", {})
        titles = [call.args[0] for call in heading.call_args_list]
        self.assertEqual(titles, [
            "Opening Snapshot", "What's Working", "Biggest Opportunity",
            "Experiments to Run", "Evidence and Confidence",
        ])
        advanced.assert_not_called()


if __name__ == "__main__":
    unittest.main()
