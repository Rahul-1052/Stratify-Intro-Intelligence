import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

from core.memory.reconstruction import reconstruct_creator_report
from core.memory.service import CreatorMemoryService
from stratify_platform.projects import create_project
from tests.test_creator_memory import record, report
from ui.memory import _render_reopened, render_current_comparison


class SavedReportReconstructionTests(unittest.TestCase):
    def test_complete_saved_report_reconstructs_creator_contract(self):
        result = reconstruct_creator_report(
            record(0), {"title": "Saved project"}, revision=2
        )
        self.assertEqual(result["status"], "reconstructed")
        restored = result["report"]
        self.assertEqual(restored["video"]["title"], "Saved project")
        self.assertEqual(restored["saved_history"]["revision"], 2)
        self.assertEqual(restored["creator_report"]["opening_snapshot"]["summary"], "A direct opening.")
        self.assertFalse(result["diagnostics"]["analysis_pipeline_rerun"])

    def test_limited_text_abstention_and_zero_experiments_are_preserved(self):
        source = replace(
            record(0), written_information_state="limited",
            recommendation_state="abstained", experiments=[],
            opportunity={"supported": False}, recommendation_confidence="limited",
        )
        result = reconstruct_creator_report(source)
        creator = result["report"]["creator_report"]
        self.assertEqual(creator["confidence_summary"]["text_evidence"], "limited")
        self.assertFalse(creator["biggest_opportunity"]["supported"])
        self.assertEqual(creator["experiments"], [])
        self.assertTrue(result["diagnostics"]["limited_text_preserved"])
        self.assertTrue(result["diagnostics"]["abstention_preserved"])

    def test_one_to_three_experiments_reopen(self):
        for count in range(1, 4):
            value = record(count)
            experiments = [
                {"title": f"Test {index}", "hypothesis": "Controlled test", "change": "Change",
                 "what_stays_constant": "Everything else", "version_a": "A", "version_b": "B",
                 "confidence": "moderate", "limitation": "No outcome evidence."}
                for index in range(count)
            ]
            result = reconstruct_creator_report(replace(value, experiments=experiments))
            self.assertEqual(len(result["report"]["creator_report"]["experiments"]), count)

    def test_partial_record_uses_normalized_fallback(self):
        partial = replace(record(0), snapshot={}, confidence_summary={})
        result = reconstruct_creator_report(partial)
        self.assertEqual(result["status"], "fallback")
        self.assertEqual(result["normalized_summary"]["opening_strategy"], "subject-first")
        self.assertIn("opening_snapshot.summary", result["diagnostics"]["missing_fields"])


class SavedReportRepositoryIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "memory.db"
        self.service = CreatorMemoryService(
            self.path, now=lambda: "2026-01-01T00:00:00+00:00"
        )
        self.service.save_profile("Creator", "Channel")

    def tearDown(self):
        self.temp.cleanup()

    def test_reopen_complete_record_without_pipeline_rerun(self):
        saved = self.service.save_report(
            report(experiments=2), create_project(upload_name="saved.mp4")
        )
        with patch("stratify_platform.module_registry.run_module") as run_module:
            result = self.service.reopen_analysis(saved["analysis_id"])
        run_module.assert_not_called()
        self.assertEqual(result["status"], "reconstructed")
        self.assertEqual(result["report"]["saved_history"]["revision"], 1)

    def test_malformed_payload_isolated_as_fallback(self):
        saved = self.service.save_report(
            report(), create_project(upload_name="malformed.mp4")
        )
        connection = sqlite3.connect(self.path)
        try:
            with connection:
                connection.execute(
                    "UPDATE analyses SET snapshot_json='not-json' WHERE id=?",
                    (saved["analysis_id"],),
                )
        finally:
            connection.close()
        result = self.service.reopen_analysis(saved["analysis_id"])
        self.assertEqual(result["status"], "fallback")
        self.assertNotIn("Traceback", result["message"])
        self.assertEqual(self.service.dashboard()["counts"]["videos"], 1)

    @patch("ui.memory.render_report")
    @patch("ui.memory.st.button", return_value=False)
    @patch("ui.memory.st.markdown")
    def test_reopened_ui_reuses_existing_renderer(self, markdown, button, renderer):
        saved = self.service.save_report(
            report(), create_project(upload_name="render.mp4")
        )
        _render_reopened(self.service, saved["analysis_id"], "creator", {})
        renderer.assert_called_once()


class CurrentComparisonRenderingTests(unittest.TestCase):
    STATES = {
        "insufficient_history": "More history is needed",
        "matches_typical_pattern": "Matches your usual pattern",
        "partially_matches_history": "Partially matches your history",
        "differs_from_usual_pattern": "Different from your recent history",
        "newly_observed_pattern": "A newly observed pattern",
        "evidence_too_limited": "Evidence is too limited",
    }

    @patch("ui.memory.st.markdown")
    @patch("ui.memory.section_heading")
    def test_each_comparison_state_renders_descriptively(self, heading, markdown):
        for state, label in self.STATES.items():
            with self.subTest(state=state):
                markdown.reset_mock()
                render_current_comparison({
                    "state": state,
                    "message": "This opening differs descriptively from saved structure.",
                    "evidence": {},
                })
                rendered = markdown.call_args.args[0]
                self.assertIn(label, rendered)
                self.assertIn("does not imply better performance", rendered)
                self.assertNotIn("successful", rendered.lower())
                self.assertNotIn("preferred", rendered.lower())

    @patch("ui.memory.st.markdown")
    @patch("ui.memory.section_heading")
    def test_limited_text_comparison_remains_limited(self, heading, markdown):
        render_current_comparison({
            "state": "evidence_too_limited",
            "message": "Text-like evidence is too limited for a historical comparison.",
            "evidence": {},
        })
        self.assertIn("too limited", markdown.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
