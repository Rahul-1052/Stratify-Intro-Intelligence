import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.beta.golden import load_golden_manifest
from core.beta.observation_accuracy import (
    ExpectedObservation, ObservedObservation, aggregate_results,
    evaluate_case, evaluate_metric, evaluate_saved_run, latest_completed_run,
    normalize_observations,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "validation" / "golden_dataset" / "manifest.json"


def observed(value, confidence=0.67):
    return ObservedObservation("metric", value, confidence, "fixture.source",
                               evidence={"fixture": True})


def expected(value, comparison, **kwargs):
    return ExpectedObservation("metric", value, comparison, **kwargs)


def report_fixture():
    frames = [
        {"timestamp": 0.0, "visual_energy": "low", "motion_score": 0.0,
         "human_presence": True, "subject_count": 1, "text_overlay": False,
         "text_overlay_confidence": "limited"},
        {"timestamp": 1.0, "visual_energy": "moderate", "motion_score": 8.0,
         "human_presence": True, "subject_count": 1, "text_overlay": True,
         "text_overlay_confidence": "limited"},
    ]
    return {
        "status": "success",
        "vision": {"visual_energy": "moderate", "frame_observations": frames},
        "intelligence_v3": {
            "confidence": {"observation_confidence": "high",
                           "interpretation_confidence": "moderate"},
            "sample_coverage": {"start_time": 0.0, "end_time": 1.0},
            "meaningful_change_events": [
                {"timestamp": 1.0, "event_type": "scene_change"}
            ],
            "visual_change_timing": {
                "change_count": 1, "timestamps": [1.0],
                "longest_stable_interval": {"duration": 1.0},
            },
            "visual_cadence": {"progression": "stable", "median_interval": 1.0},
            "visual_novelty": {"average": 0.4, "scores": [0.4]},
            "information_introduction": {"time_to_first_event": 1.0,
                                         "event_count": 1},
            "subject_continuity": "stable_visible_subject",
            "visual_density": {
                "classification": "high_density_competing_focal_regions",
                "average_elements": 2.0, "focal_stability": "variable",
            },
        },
    }


class ComparisonTests(unittest.TestCase):
    def test_exact_categorical_match(self):
        result = evaluate_metric(expected("high", "exact"), observed("high"))
        self.assertEqual(result.score, 1.0)

    def test_categorical_mismatch(self):
        result = evaluate_metric(expected("high", "exact"), observed("low"))
        self.assertEqual(result.score, 0.0)
        self.assertTrue(result.mismatch_reason)

    def test_ordered_category_partial(self):
        result = evaluate_metric(
            expected("low", "ordered", tolerance=1), observed("moderate")
        )
        self.assertEqual(result.score, 0.5)
        self.assertEqual(result.status, "partial")

    def test_numeric_minimum(self):
        self.assertEqual(
            evaluate_metric(expected(5, "numeric_min"), observed(6)).score, 1
        )

    def test_numeric_maximum(self):
        self.assertEqual(
            evaluate_metric(expected(5, "numeric_max"), observed(6)).score, 0
        )

    def test_numeric_range(self):
        self.assertEqual(
            evaluate_metric(expected([3, 5], "numeric_range"), observed(4)).score, 1
        )

    def test_boolean(self):
        self.assertEqual(
            evaluate_metric(expected(True, "boolean"), observed(True)).score, 1
        )

    def test_temporal_early(self):
        self.assertEqual(
            evaluate_metric(expected(1.5, "temporal_before"), observed(1.0)).score, 1
        )

    def test_temporal_late(self):
        self.assertEqual(
            evaluate_metric(expected(3.0, "temporal_after"), observed(4.0)).score, 1
        )

    def test_relative_comparison(self):
        result = evaluate_metric(
            expected({"operator": "gt", "value": 0.5}, "relative"), observed(0.7)
        )
        self.assertEqual(result.score, 1)

    def test_presence_and_absence(self):
        self.assertEqual(
            evaluate_metric(expected("present", "presence"), observed(0)).score, 1
        )
        self.assertEqual(
            evaluate_metric(expected("absent", "presence"), observed(None)).score, 1
        )

    def test_missing_observation_is_unavailable(self):
        result = evaluate_metric(expected("high", "exact", required=True), None)
        self.assertIsNone(result.score)
        self.assertEqual(result.status, "unavailable")

    def test_invalid_comparison_mode(self):
        with self.assertRaises(ValueError):
            evaluate_metric(expected("x", "invented"), observed("x"))

    def test_invalid_ordered_value(self):
        with self.assertRaises(ValueError):
            evaluate_metric(expected("unknown", "ordered"), observed("low"))

    def test_confidence_remains_separate(self):
        result = evaluate_metric(expected("high", "exact"), observed("high", 0.2))
        self.assertEqual(result.score, 1.0)
        self.assertEqual(result.confidence, 0.2)


class AdapterAndCaseTests(unittest.TestCase):
    def test_adapter_uses_structured_sources(self):
        metrics = normalize_observations(report_fixture())
        self.assertEqual(metrics["motion_score_mean"].observed_value, 4.0)
        self.assertEqual(metrics["scene_change_count"].observed_value, 1)
        self.assertEqual(metrics["subject_intro_seconds"].observed_value, 0.0)
        self.assertEqual(metrics["text_intro_seconds"].observed_value, 1.0)
        self.assertTrue(all(item.source for item in metrics.values()))

    def test_weighted_scoring_and_partial(self):
        case = {"case_id": "case", "expected_observations": [
            {"metric": "visual_energy", "expected_value": "low",
             "comparison": "ordered", "tolerance": 1, "weight": 2},
            {"metric": "change_count", "expected_value": 0,
             "comparison": "numeric_max", "weight": 1},
        ]}
        result = evaluate_case(case, report_fixture())
        self.assertEqual(result.partial_metrics, 1)
        self.assertEqual(result.mismatched_metrics, 1)
        self.assertAlmostEqual(result.weighted_score, 1 / 3, places=3)

    def test_unavailable_excluded_and_required_coverage(self):
        case = {"case_id": "case", "expected_observations": [
            {"metric": "unsupported_metric", "expected_value": 1,
             "comparison": "exact", "required": True},
            {"metric": "change_count", "expected_value": 1,
             "comparison": "exact", "required": True},
        ]}
        result = evaluate_case(case, report_fixture())
        self.assertEqual(result.unweighted_score, 1.0)
        self.assertEqual(result.evaluability_coverage, 0.5)
        self.assertEqual(result.required_metric_coverage, 0.5)
        self.assertEqual(len(result.warnings), 1)

    def test_zero_expectations_is_unevaluable(self):
        result = evaluate_case({"case_id": "old"}, report_fixture())
        self.assertEqual(result.status, "unevaluable")
        self.assertIsNone(result.weighted_score)

    def test_zero_available_metrics_is_unevaluable(self):
        result = evaluate_case({"case_id": "case", "expected_observations": [{
            "metric": "unsupported", "expected_value": True,
            "comparison": "boolean", "required": True,
        }]}, report_fixture())
        self.assertEqual(result.status, "unevaluable")

    def test_status_assignment(self):
        excellent = evaluate_case({"case_id": "case", "expected_observations": [{
            "metric": "change_count", "expected_value": 1,
            "comparison": "exact", "required": True,
        }]}, report_fixture())
        self.assertEqual(excellent.status, "excellent")


class AggregateAndManifestTests(unittest.TestCase):
    def test_aggregate_metric_accuracy_and_rankings(self):
        good = evaluate_case({"case_id": "good", "expected_observations": [{
            "metric": "change_count", "expected_value": 1, "comparison": "exact",
        }]}, report_fixture())
        bad = evaluate_case({"case_id": "bad", "expected_observations": [{
            "metric": "visual_energy", "expected_value": "high", "comparison": "exact",
        }]}, report_fixture())
        summary = aggregate_results("run", [good, bad], "fixed")
        self.assertEqual(summary.mismatch_count, 1)
        self.assertEqual(summary.unavailable_count, 0)
        self.assertEqual(summary.accuracy_by_metric["change_count"]["accuracy"], 1)
        self.assertEqual(summary.weakest_metrics[0]["metric"], "visual_energy")
        self.assertEqual(summary.strongest_metrics[0]["metric"], "change_count")

    def test_first_ten_manifest_cases_have_expectations(self):
        cases = load_golden_manifest(MANIFEST)["cases"]
        self.assertTrue(all(case.get("expected_observations") for case in cases[:10]))
        self.assertTrue(all("expected_observations" not in case for case in cases[10:]))

    def test_old_manifest_without_expectations_still_loads(self):
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for case in payload["cases"]:
            case.pop("expected_observations", None)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "manifest.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            loaded = load_golden_manifest(path)
        self.assertEqual(len(loaded["cases"]), 30)


class SavedRunIntegrationTests(unittest.TestCase):
    def _saved_run(self, root, run_id="20260101T000000Z-fixture",
                   case_status="completed", include_report=True):
        run = Path(root) / run_id
        (run / "reports").mkdir(parents=True)
        summary = {
            "run_id": run_id, "timestamp": "2026-01-01T00:00:00+00:00",
            "cases": [{"case_id": "fixture-case", "status": case_status,
                       "report_path": "reports/fixture-case.json"}],
        }
        (run / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
        if include_report:
            (run / "reports" / "fixture-case.json").write_text(
                json.dumps(report_fixture()), encoding="utf-8"
            )
        manifest = Path(root) / "manifest.json"
        manifest.write_text(json.dumps({"cases": [{
            "case_id": "fixture-case", "case_title": "Fixture",
            "expected_observations": [{
                "metric": "change_count", "expected_value": 1,
                "comparison": "exact", "required": True,
            }],
        }]}), encoding="utf-8")
        return run, manifest

    def test_evaluate_completed_saved_case_and_exports(self):
        with tempfile.TemporaryDirectory() as folder:
            run, manifest = self._saved_run(folder)
            summary, accuracy = evaluate_saved_run(run, manifest)
            self.assertEqual(summary.aggregate_weighted_accuracy, 1.0)
            self.assertTrue((accuracy / "summary.json").is_file())
            self.assertTrue((accuracy / "summary.md").is_file())
            self.assertTrue((accuracy / "cases" / "fixture-case.json").is_file())

    def test_failed_or_missing_report_is_safe(self):
        with tempfile.TemporaryDirectory() as folder:
            run, manifest = self._saved_run(
                folder, case_status="failed", include_report=False
            )
            summary, _ = evaluate_saved_run(run, manifest)
            self.assertEqual(summary.cases_evaluated, 0)
            self.assertTrue(summary.warnings)

    def test_latest_completed_run_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            self._saved_run(folder, "20260101T000000Z-old")
            latest, _ = self._saved_run(folder, "20260102T000000Z-new")
            self.assertEqual(latest_completed_run(folder), latest)

    def test_deterministic_saved_output(self):
        with tempfile.TemporaryDirectory() as folder:
            run, manifest = self._saved_run(folder)
            _, accuracy = evaluate_saved_run(run, manifest)
            first = (accuracy / "summary.json").read_bytes()
            evaluate_saved_run(run, manifest)
            self.assertEqual(first, (accuracy / "summary.json").read_bytes())

    def test_saved_evaluation_never_calls_network_or_pipeline(self):
        with tempfile.TemporaryDirectory() as folder:
            run, manifest = self._saved_run(folder)
            with patch("stratify_platform.module_registry.run_module") as module:
                evaluate_saved_run(run, manifest)
            module.assert_not_called()


if __name__ == "__main__":
    unittest.main()
