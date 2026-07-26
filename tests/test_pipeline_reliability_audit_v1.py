import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.product_validation.evidence_audit import DIMENSIONS, aggregate_evidence, audit_exports, case_availability
from core.product_validation.fixtures import fixture_cases
from core.product_validation.pipeline_trace import PipelineStageTrace, PipelineTrace, STAGES, classify_failure
from core.product_validation.runner import ProductValidationRunner, trace_reconstruction
from core.product_validation.storage import ValidationStore
from ui.product_validation import render_product_validation


class PipelineTraceModelTests(unittest.TestCase):
    def test_serialization_statuses_duration_and_warning_preservation(self):
        stage = PipelineStageTrace("acquisition")
        stage.transition("running")
        time.sleep(0.001)
        stage.transition("completed_with_warnings", warnings=["cached source"], evidence_counts={"clips": 1})
        value = stage.to_dict()
        self.assertGreater(value["duration_seconds"], 0)
        self.assertEqual(value["warnings"], ["cached source"])
        self.assertEqual(value["evidence_counts"]["clips"], 1)
        json.dumps(value)

    def test_valid_and_invalid_transitions(self):
        with self.assertRaises(ValueError):
            PipelineStageTrace("x").transition("completed")
        stage = PipelineStageTrace("x")
        stage.transition("running").transition("failed", error=RuntimeError("boom"))
        with self.assertRaises(ValueError):
            stage.transition("running")

    def test_failed_stage_and_failure_taxonomy(self):
        trace = PipelineTrace("r", "c", "real-video pipeline validation")
        trace.stage("acquisition").transition("running").transition("completed")
        trace.stage("clip preparation").transition("running").transition("failed", error=RuntimeError("bad"))
        self.assertEqual(trace.last_successful_stage, "acquisition")
        self.assertEqual(trace.first_failed_stage, "clip preparation")
        self.assertEqual(classify_failure(RuntimeError("yt-dlp 403"), stage="acquisition"), "downloader failure")
        self.assertEqual(classify_failure(RuntimeError("bad"), stage="frame extraction"), "frame extraction failure")


class TracedRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ValidationStore(Path(self.temp.name) / "validation")
    def tearDown(self):
        self.temp.cleanup()

    def test_trace_saved_and_product_validation_integrated(self):
        run = ProductValidationRunner(self.store).run(fixture_cases()[:1], run_id="trace-run")
        case = run["cases"][0]
        trace = json.loads((self.store.root / case["pipeline_trace_reference"]).read_text())
        self.assertEqual([stage["stage_name"] for stage in trace["stages"]], list(STAGES))
        self.assertEqual(trace["provenance"], "fixture UI validation")
        self.assertEqual(next(s for s in trace["stages"] if s["stage_name"] == "persistence")["stage_status"], "completed")
        self.assertEqual(next(s for s in trace["stages"] if s["stage_name"] == "reconstruction")["stage_status"], "skipped")

    def test_continuation_no_network_and_safe_resume(self):
        entries = [{"case_id": "missing", "local_source": "does-not-exist.mp4", "niche": "unknown", "source_type": "local"},
                   {"case_id": "good", "url": "https://example.invalid/video", "niche": "unknown", "source_type": "test"}]
        analyzer = MagicMock(return_value=fixture_cases()[0]["report"])
        runner = ProductValidationRunner(self.store, analyzer)
        first = runner.run(entries, run_id="resume-run", no_network=True)
        self.assertEqual([case["analysis_status"] for case in first["cases"]], ["failed", "completed"])
        runner.run(entries, run_id="resume-run", resume=True, no_network=True)
        self.assertEqual(analyzer.call_count, 1)

    def test_reconstruction_trace_success_and_failure(self):
        result, trace = trace_reconstruction("r", "c", {}, reconstructor=lambda record, video, revision: {"ok": True})
        self.assertTrue(result["ok"])
        self.assertEqual(trace.stage("reconstruction").stage_status, "completed")
        result, trace = trace_reconstruction("r", "c", {}, reconstructor=lambda *args: (_ for _ in ()).throw(ValueError("bad record")))
        self.assertIsNone(result)
        self.assertEqual(trace.failure_category, "reconstruction failure")

    def test_failed_production_report_is_persisted_and_classified(self):
        source = Path(self.temp.name) / "clip.mp4"
        source.write_bytes(b"fixture")
        analyzer = MagicMock(return_value={"status": "failed", "warnings": [
            "Unexpected Stratify error: Missing YOUTUBE_API_KEY in .streamlit/secrets.toml"]})
        run = ProductValidationRunner(self.store, analyzer).run([
            {"case_id": "local", "local_source": str(source), "niche": "unknown", "source_type": "local"}
        ], run_id="failed-report")
        case = run["cases"][0]
        self.assertEqual(case["failure_category"], "environment failure")
        self.assertEqual(case["first_failed_stage"], "acquisition")
        self.assertTrue(case["report_reference"])
        trace = json.loads((self.store.root / case["pipeline_trace_reference"]).read_text())
        persistence = next(stage for stage in trace["stages"] if stage["stage_name"] == "persistence")
        self.assertEqual(persistence["stage_status"], "completed")

    def test_creator_memory_schema_is_unchanged(self):
        from core.memory.schema import SCHEMA_VERSION
        self.assertEqual(SCHEMA_VERSION, 1)


class EvidenceAuditTests(unittest.TestCase):
    def test_evidence_aggregation_three_state_vocabulary(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ValidationStore(directory)
            run = ProductValidationRunner(store).run(fixture_cases()[:2], run_id="evidence")
            aggregate = aggregate_evidence(run, store.load_report)
            self.assertEqual(set(aggregate["summary"]), set(DIMENSIONS))
            allowed = {"unavailable", "available but weak", "available and qualified"}
            self.assertTrue(all(set(counts) <= allowed for counts in aggregate["summary"].values()))

    def test_exports_preserve_real_provenance_and_failures(self):
        run = {"run_id": "r", "validation_mode": "real-video pipeline validation",
               "cases": [{"case_id": "c", "analysis_status": "failed", "failure_category": "frame extraction failure",
                          "last_successful_stage": "clip preparation", "first_failed_stage": "frame extraction"}]}
        aggregate = {"summary": {}}
        exported = audit_exports(run, [{"path": "clip.mp4"}], aggregate)
        self.assertIn("frame extraction failure", exported["failure_summary.csv"])
        self.assertIn("Stage evidence", exported["pipeline_audit.md"])

    @patch("ui.product_validation.st")
    def test_creator_mode_trace_isolation(self, st):
        render_product_validation("creator", MagicMock())
        st.header.assert_not_called()
