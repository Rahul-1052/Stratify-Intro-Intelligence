import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.beta.golden import (
    GoldenDatasetRunner, compare_runs, load_golden_manifest,
)
from core.beta.services import (
    BetaService, extract_feedback_themes, report_identifier,
)
from core.beta.storage import BetaStore
from core.product_validation.checks import run_quality_checks
from ui.beta import render_beta_dashboard


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "validation" / "golden_dataset" / "manifest.json"


class GoldenDatasetTests(unittest.TestCase):
    def test_initial_manifest_is_valid_and_has_thirty_cases(self):
        manifest = load_golden_manifest(MANIFEST)
        self.assertEqual(len(manifest["cases"]), 30)
        self.assertEqual(len({item["case_id"] for item in manifest["cases"]}), 30)

    def test_manifest_rejects_missing_required_field(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "manifest.json"
            path.write_text(json.dumps({"cases": [{"case_id": "bad"}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_golden_manifest(path)

    def test_manifest_rejects_duplicate_ids(self):
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        payload["cases"][1]["case_id"] = payload["cases"][0]["case_id"]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "manifest.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_golden_manifest(path)

    def test_missing_clips_are_skipped_without_analyzer(self):
        case = load_golden_manifest(MANIFEST)["cases"][0]
        analyzer = MagicMock()
        with tempfile.TemporaryDirectory() as folder:
            run, _ = GoldenDatasetRunner(analyzer).run([case], folder, no_network=True)
        self.assertEqual(run["cases"][0]["status"], "skipped")
        analyzer.assert_not_called()

    def test_disabled_cases_are_not_run(self):
        case = {**load_golden_manifest(MANIFEST)["cases"][0], "enabled": False}
        with tempfile.TemporaryDirectory() as folder:
            run, _ = GoldenDatasetRunner(MagicMock()).run([case], folder)
        self.assertEqual(run["cases"], [])

    def test_runner_serializes_report_trace_json_and_csv(self):
        with tempfile.TemporaryDirectory() as folder:
            clip = Path(folder) / "clip.mp4"
            clip.write_bytes(b"fixture")
            case = {
                **load_golden_manifest(MANIFEST)["cases"][0],
                "local_clip_path": str(clip),
                "_manifest_dir": folder,
            }
            report = {
                "status": "success",
                "vision": {"frame_observations": [{"timestamp": 0}]},
                "intelligence_v3": {"findings": [], "meaningful_change_events": []},
                "creator_report": {
                    "biggest_opportunity": {"supported": False},
                    "confidence_breakdown": {"observation_confidence": "limited"},
                },
            }
            run, location = GoldenDatasetRunner(
                lambda unused_case, unused_clip: report
            ).run([case], Path(folder) / "runs")
            self.assertEqual(run["cases"][0]["recommendation_state"], "abstention")
            self.assertTrue((location / "summary.json").is_file())
            self.assertTrue((location / "summary.csv").is_file())
            self.assertTrue((location / run["cases"][0]["report_path"]).is_file())
            self.assertTrue((location / run["cases"][0]["trace_path"]).is_file())

    def test_prior_run_comparison(self):
        prior = {"cases": [{"case_id": "one", "status": "completed",
                            "recommendation_state": "abstention", "warning_count": 0}]}
        current = {"cases": [
            {"case_id": "one", "status": "completed",
             "recommendation_state": "experiment", "warning_count": 0},
            {"case_id": "two", "status": "skipped"},
        ]}
        comparison = compare_runs(current, prior)
        self.assertEqual(comparison[0]["state"], "changed")
        self.assertEqual(comparison[1]["state"], "new")


class BetaStorageAndServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.store = BetaStore(self.temporary.name)
        self.service = BetaService(self.store)

    def tearDown(self):
        self.temporary.cleanup()

    def test_feedback_submission_and_duplicate_prevention(self):
        first = self.service.submit_feedback(
            "report", "local", "abstention", {"usefulness": 4}, "session"
        )
        second = self.service.submit_feedback(
            "report", "local", "abstention", {"usefulness": 1}, "session"
        )
        self.assertEqual(first["status"], "saved")
        self.assertEqual(second["status"], "duplicate")
        self.assertEqual(len(self.store.list("feedback")), 1)

    def test_analytics_event_persistence(self):
        event = self.service.track(
            "report_viewed", "session", "report", "local", {"mode": "creator"}
        )
        self.assertEqual(self.store.load("analytics", event["event_id"])["event_name"],
                         "report_viewed")

    def test_analytics_rejects_privacy_fields(self):
        with self.assertRaises(ValueError):
            self.service.track(
                "report_viewed", "session", metadata={"email": "not-allowed"}
            )
        with self.assertRaises(ValueError):
            self.service.track(
                "report_viewed", "session",
                metadata={"context": {"device_fingerprint": "not-allowed"}},
            )

    def test_analytics_failure_isolation(self):
        with patch.object(self.service, "track", side_effect=OSError("disk")):
            self.assertIsNone(self.service.safe_track("report_viewed", "session"))

    def test_corrupted_file_is_ignored(self):
        path = self.store.root / "feedback" / "broken.json"
        path.write_text("{", encoding="utf-8")
        self.assertIsNone(self.store.load("feedback", "broken"))
        self.assertEqual(self.store.list("feedback"), [])

    def test_legacy_schema_is_migrated(self):
        path = self.store.root / "feedback" / "legacy.json"
        path.write_text(json.dumps({"feedback_id": "legacy"}), encoding="utf-8")
        self.assertEqual(self.store.load("feedback", "legacy")["schema_version"], 1)

    def test_incomplete_review_not_in_averages(self):
        review = self.service.save_review(
            "case", "reviewer", {"strongest_insight_usefulness": 5}
        )
        summary = self.service.dashboard_summary()
        self.assertFalse(review["completed"])
        self.assertEqual(summary["review_sample_size"], 0)

    def test_completed_review_aggregates(self):
        values = {
            "strongest_insight_usefulness": 5, "evidence_specificity": 4,
            "experiment_actionability": 3, "trustworthiness": 4,
            "clarity": 5, "novelty": 2, "generic_language_present": False,
            "recommendation_sensible": True, "contradiction_present": False,
            "report_worth_revisiting": True,
        }
        self.service.save_review("case", "reviewer", values)
        summary = self.service.dashboard_summary()
        self.assertEqual(summary["review_sample_size"], 1)
        self.assertEqual(summary["review_averages"]["clarity"], 5)

    def test_feedback_dashboard_aggregation_and_small_sample_inputs(self):
        self.service.submit_feedback("one", "local", "experiment", {
            "usefulness": 5, "most_useful_section": "Primary Experiment",
            "try_experiment": "Yes", "use_before_next_upload": "Yes",
            "would_pay": "No", "confusing": "Benchmark wording was confusing",
        }, "session-one")
        summary = self.service.dashboard_summary()
        self.assertEqual(summary["feedback_sample_size"], 1)
        self.assertEqual(summary["average_usefulness"], 5)
        self.assertEqual(summary["experiment_intent_percentage"], 100.0)
        self.assertEqual(summary["confusion_themes"][0]["theme"], "benchmark confusion")

    def test_theme_extraction_is_deterministic(self):
        records = [{"answers": {"confusing": "Upload was slow and navigation unclear"}}]
        first = extract_feedback_themes(records)
        self.assertEqual(first, extract_feedback_themes(records))
        self.assertEqual(
            [item["theme"] for item in first],
            ["UI navigation", "performance", "unclear wording", "upload problem"],
        )

    def test_tester_csv_import_and_deterministic_export(self):
        source = Path(self.temporary.name) / "testers.csv"
        source.write_text(
            "tester_id,display_name,invite_status,reports_generated,feedback_submitted\n"
            "t-1,Alpha,invited,2,1\n", encoding="utf-8"
        )
        self.service.import_testers_csv(source)
        export = self.store.export_csv("testers")
        first = export.read_text(encoding="utf-8")
        self.store.export_csv("testers", export)
        self.assertEqual(first, export.read_text(encoding="utf-8"))
        self.assertEqual(self.store.load("testers", "t-1")["display_name"], "Alpha")

    def test_creator_memory_storage_is_isolated(self):
        self.assertNotIn("memory", str(self.store.root).lower())
        self.assertFalse((self.store.root / "creator_memory").exists())

    def test_report_identifier_does_not_store_prose(self):
        identifier = report_identifier({
            "video": {"video_id": "abc", "title": "Sensitive title"},
            "creator_report": {"opening_snapshot": {"summary": "Full report prose"}},
        })
        self.assertEqual(len(identifier), 16)
        self.assertNotIn("Sensitive", identifier)

    def test_exports_exclude_raw_video_frames(self):
        self.service.submit_feedback(
            "report", "local", "abstention", {"usefulness": 3}, "session"
        )
        export = self.store.export_csv("feedback")
        self.assertNotIn("frame", export.read_text(encoding="utf-8").lower())

    def test_analytics_summary_csv_export(self):
        self.service.track("analysis_completed", "session")
        export = self.service.export_analytics_summary_csv()
        text = export.read_text(encoding="utf-8")
        self.assertIn("completed_analyses,1", text)

    def test_product_validation_compatibility(self):
        warnings = run_quality_checks({"status": "partial", "creator_report": {}})
        self.assertIsInstance(warnings, list)


class BetaUiIsolationTests(unittest.TestCase):
    @patch("ui.beta.st")
    def test_creator_mode_cannot_open_builder_dashboard(self, mock_st):
        render_beta_dashboard("creator", service=MagicMock())
        mock_st.info.assert_called_once()
        mock_st.title.assert_not_called()

    @patch("ui.beta.st")
    def test_builder_dashboard_is_visible_and_small_sample_labeled(self, mock_st):
        service = MagicMock()
        service.dashboard_summary.return_value = {
            "total_reports_generated": 0, "failed_analyses": 0,
            "feedback_count": 0, "average_usefulness": None,
            "feedback_sample_size": 0, "repeat_analyses_by_session": 0,
            "experiment_intent_percentage": None,
            "next_upload_reuse_intent": None,
            "willingness_to_pay_count": 0, "most_useful_sections": {},
            "confusion_themes": [], "review_sample_size": 0,
            "review_averages": {}, "golden_dataset": {},
            "unresolved_validation_warnings": 0,
        }
        mock_st.columns.side_effect = [
            [MagicMock() for _ in range(4)], [MagicMock() for _ in range(4)]
        ]
        mock_st.tabs.return_value = [MagicMock() for _ in range(5)]
        render_beta_dashboard("builder", service=service)
        mock_st.title.assert_called_once_with("Private Beta Review")
        caption = " ".join(call.args[0] for call in mock_st.caption.call_args_list)
        self.assertIn("not statistically significant", caption)


if __name__ == "__main__":
    unittest.main()
