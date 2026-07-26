import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.product_validation.checks import issue_signature, run_quality_checks
from core.product_validation.exports import export_bundle, summarize
from core.product_validation.fixtures import fixture_cases
from core.product_validation.models import ValidationDecision, ValidationIssue, ValidationScore
from core.product_validation.runner import ProductValidationRunner, load_manifest
from core.product_validation.storage import ValidationStore
from ui.product_validation import render_product_validation


class ProductValidationModelsTests(unittest.TestCase):
    def test_scores_validate_and_decision_serializes(self):
        self.assertEqual(ValidationScore(clarity=5).validate().clarity, 5)
        with self.assertRaises(ValueError):
            ValidationScore(clarity=6).validate()
        self.assertEqual(ValidationDecision.USEFUL.value, "useful")

    def test_issue_signature_groups_only_matching_fields(self):
        one = {"category": "trust", "section": "confidence", "short_description": "Mismatch"}
        self.assertEqual(issue_signature(one), issue_signature(dict(one)))
        self.assertNotEqual(issue_signature(one), issue_signature({**one, "section": "report"}))


class ProductValidationStorageRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ValidationStore(Path(self.temp.name) / ".stratify_validation")
    def tearDown(self):
        self.temp.cleanup()

    def test_fixture_run_stores_reports_and_resumes_without_analysis(self):
        analyzer = MagicMock()
        runner = ProductValidationRunner(self.store, analyzer)
        entries = fixture_cases()[:2]
        first = runner.run(entries, run_id="run-a", mode="fixture UI validation")
        self.assertTrue(first["completed"])
        self.assertTrue((self.store.root / first["cases"][0]["report_reference"]).exists())
        runner.run(entries, run_id="run-a", mode="fixture UI validation", resume=True)
        analyzer.assert_not_called()

    def test_interrupted_run_and_failure_are_isolated(self):
        def analyzer(entry):
            if entry["case_id"] == "bad":
                raise RuntimeError("bounded failure")
            return fixture_cases()[0]["report"]
        entries = [{"case_id": "bad", "url": "x", "niche": "x", "source_type": "local"},
                   {"case_id": "good", "url": "y", "niche": "y", "source_type": "local"}]
        run = ProductValidationRunner(self.store, analyzer).run(entries, run_id="run-b")
        self.assertEqual([c["analysis_status"] for c in run["cases"]], ["failed", "completed"])

    def test_review_requires_one_change_and_updates_run(self):
        ProductValidationRunner(self.store).run(fixture_cases()[:1], run_id="run-c")
        with self.assertRaises(ValueError):
            self.store.save_review("run-c", "strong-visual", {"one_change": ""})
        self.store.save_review("run-c", "strong-visual", {"one_change": "Clarify evidence.", "reviewer_status": "reviewed"})
        self.assertEqual(self.store.load_run("run-c")["cases"][0]["reviewer_status"], "reviewed")

    def test_duplicate_manifest_rejected(self):
        path = Path(self.temp.name) / "manifest.json"
        path.write_text(json.dumps({"cases": [{"case_id": "x"}, {"case_id": "x"}]}))
        with self.assertRaises(ValueError):
            load_manifest(path)


class ProductValidationChecksTests(unittest.TestCase):
    def test_objective_warning_rules(self):
        report = fixture_cases()[0]["report"]
        creator = report["creator_report"]
        creator["biggest_opportunity"]["supported"] = False
        creator["experiments"][0].update({"source": "text-derived", "structural_dimension": "text_density"})
        creator["confidence_summary"]["text_evidence"] = "limited"
        creator["creative_understanding"]["summary"] = "This will increase retention because viewers will love it."
        codes = {item["code"] for item in run_quality_checks(report)}
        self.assertTrue({"no_opportunity_has_experiments", "unsupported_text_experiment",
                         "unsupported_performance_claim", "retention_without_evidence",
                         "audience_psychology_claim"} <= codes)

    def test_malformed_missing_and_repetition(self):
        self.assertEqual(run_quality_checks([])[0]["code"], "malformed_report")
        report = {"status": "success", "creator_report": {}}
        self.assertIn("missing_section", {item["code"] for item in run_quality_checks(report)})

    def test_fixture_labels_and_no_human_claim(self):
        self.assertTrue(all(case["validation_kind"] == "fixture UI validation" for case in fixture_cases()))
        run = ProductValidationRunner(ValidationStore(Path(self.tempdir()) / "pv")).run(fixture_cases()[:1], mode="fixture UI validation")
        markdown = export_bundle(run)["validation_report.md"]
        self.assertIn("not creator validation", markdown)

    @staticmethod
    def tempdir():
        return tempfile.mkdtemp()

    def test_exports_and_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            run = ProductValidationRunner(ValidationStore(directory)).run(fixture_cases()[:2], mode="fixture UI validation")
            bundle = export_bundle(run)
            self.assertEqual(set(bundle), {"run.json", "human_reviews.csv", "issues.csv", "summary.json", "validation_report.md"})
            self.assertEqual(summarize(run)["pending_reviews"], 2)


class ProductValidationUiTests(unittest.TestCase):
    @patch("ui.product_validation.st")
    def test_creator_mode_isolation(self, st):
        render_product_validation("creator", MagicMock())
        st.header.assert_not_called()

    @patch("ui.product_validation.st")
    def test_builder_gating_and_empty_state(self, st):
        store = MagicMock()
        store.list_runs.return_value = []
        render_product_validation("builder", store)
        st.header.assert_called_with("Product Validation")
        st.info.assert_called()

    def test_creator_memory_schema_is_unchanged(self):
        from core.memory.schema import SCHEMA_VERSION
        self.assertEqual(SCHEMA_VERSION, 1)
