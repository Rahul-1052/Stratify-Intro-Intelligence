import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.evaluation.dataset import EvaluationDatasetStore
from core.evaluation.evaluation_metrics import analyze_failures, calculate_metrics, compare_manual_labels
from core.evaluation.evaluation_models import EvaluationResult, EvaluationVideo
from core.evaluation.evaluation_runner import EvaluationRunner
from core.evaluation.exports import export_csv, export_json, export_markdown
from core.evaluation.report_comparison import compare_runs
from ui.evaluation import render_evaluation_dashboard


def report(focus="person", clarity="immediate", text="supportive", beats=2, benchmark=False):
    semantic_beats = [{"beat_purpose": "subject_establishment"} for _ in range(beats)]
    return {
        "status": "success",
        "vision": {"frame_observations": [{"timestamp": 0}]},
        "semantic_observation": {
            "primary_visual_focus": focus, "focus_clarity": clarity,
            "text_role": text, "opening_mode": "subject_first",
            "visual_progression": "gradual_change", "semantic_confidence": "moderate",
            "beats": semantic_beats, "unavailable_fields": [],
        },
        "creator_report": {
            "opening_snapshot": {"summary": "A visible person leads the opening."},
            "intro_timeline": semantic_beats,
            "whats_working": [{"title": "Clear hierarchy"}],
            "biggest_opportunity": {"title": "Delay text"},
            "experiments": [{"title": "Delay text", "confidence": "moderate"}],
            "evidence_validation": {"benchmark_supported": benchmark, "label": "validated" if benchmark else "benchmark unavailable"},
        },
    }


class EvaluationFrameworkTests(unittest.TestCase):
    def test_dataset_loading_saving_and_empty_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.json"
            store = EvaluationDatasetStore(path)
            self.assertEqual(store.load()["videos"], [])
            video = EvaluationVideo("v1", "Video one", "youtube", "education", "https://example/v1", {"focus_clarity": "immediate"})
            store.save("suite", [video])
            loaded = store.load()
            self.assertEqual(loaded["name"], "suite")
            self.assertEqual(loaded["videos"][0].video_id, "v1")
            self.assertEqual(loaded["videos"][0].expected_manual_labels["focus_clarity"], "immediate")

    def test_partial_manual_labels_produce_explainable_agreement(self):
        comparisons = compare_manual_labels({
            "focus_clarity": "immediate", "number_of_semantic_beats": 3,
            "primary_visual_focus": "multiple_people", "text_role": None,
        }, report(focus="person", clarity="develops_early", beats=2))
        by_field = {item.field: item for item in comparisons}
        self.assertEqual(by_field["focus_clarity"].result, "partial")
        self.assertEqual(by_field["number_of_semantic_beats"].result, "partial")
        self.assertEqual(by_field["primary_visual_focus"].result, "incorrect")
        self.assertNotIn("text_role", by_field)
        self.assertTrue(all(item.explanation for item in comparisons))

    def test_runner_saves_artifacts_and_reuses_cache(self):
        calls = []
        def analyzer(url):
            calls.append(url)
            return report()
        with tempfile.TemporaryDirectory() as directory:
            store = EvaluationDatasetStore(Path(directory) / "dataset.json")
            video = EvaluationVideo("v1", "Video one", "offline", "education", "fixture://v1", {"focus_clarity": "immediate"})
            store.save("suite", [video])
            runner = EvaluationRunner(analyzer, Path(directory) / "artifacts", store, clock=MagicMock(side_effect=[1.0, 2.5]))
            first = runner.run(store.load(), run_id="run-a")
            second = runner.run(store.load(), run_id="run-b")
            self.assertEqual(len(calls), 1)
            self.assertFalse(first.results[0].cache_used)
            self.assertTrue(second.results[0].cache_used)
            self.assertTrue((Path(directory) / "artifacts" / "cache" / "v1.json").exists())
            self.assertTrue((Path(directory) / "artifacts" / "runs" / "run-b.json").exists())
            self.assertEqual(len(store.load()["videos"][0].evaluation_history), 2)

    def test_metrics_mixed_categories_observation_and_benchmark(self):
        first_report, second_report = report(benchmark=False), report(focus="multiple_people", benchmark=True)
        first_agreement = compare_manual_labels({"focus_clarity": "immediate"}, first_report)
        second_agreement = compare_manual_labels({"primary_visual_focus": "person"}, second_report)
        results = [
            EvaluationResult("a", "A", "education", "success", 1.0, first_report, first_agreement),
            EvaluationResult("b", "B", "entertainment", "success", 3.0, second_report, second_agreement),
        ]
        metrics = calculate_metrics(results)
        self.assertEqual(metrics["video_count"], 2)
        self.assertEqual(metrics["observation_coverage"]["rate"], 1.0)
        self.assertEqual(metrics["benchmark_success_rate"], {"numerator": 1, "denominator": 2, "rate": 0.5})
        self.assertEqual(metrics["observation_only_rate"]["rate"], 0.5)
        self.assertEqual(metrics["average_report_generation_seconds"], 2.0)
        self.assertEqual(set(metrics["per_category_agreement"]), {"education", "entertainment"})

    def test_empty_metrics_do_not_fake_precision(self):
        metrics = calculate_metrics([])
        self.assertIsNone(metrics["manual_agreement_rate"]["rate"])
        self.assertIsNone(metrics["average_beat_count"])
        self.assertEqual(metrics["video_count"], 0)

    def test_failure_analysis(self):
        value = report()
        value["semantic_observation"]["text_role"] = "unavailable"
        agreements = compare_manual_labels({"primary_visual_focus": "multiple_people"}, value)
        result = EvaluationResult("v", "Video", "film", "success", 1.0, value, agreements)
        analysis = analyze_failures([result])
        self.assertEqual(analysis["most_common_wrong_semantic_field"][0][0], "primary_visual_focus")
        self.assertEqual(analysis["most_common_unavailable_field"][0][0], "text_role")
        self.assertEqual(analysis["most_common_category_failure"][0][0], "film")
        self.assertEqual(analysis["most_common_experiment"][0][0], "Delay text")

    def test_exports_are_portable(self):
        payload = {"run_id": "run-a", "dataset_name": "suite", "metrics": {"video_count": 1}, "results": [{
            "video_id": "v1", "video_title": "Video", "category": "film", "status": "success",
            "generation_seconds": 1.2, "cache_used": False,
            "agreements": [{"field": "focus_clarity", "expected": "immediate", "predicted": "immediate", "result": "correct"}],
        }]}
        self.assertEqual(json.loads(export_json(payload))["run_id"], "run-a")
        self.assertIn("focus_clarity", export_csv(payload))
        self.assertIn("# Stratify Evaluation", export_markdown(payload))

    def test_regression_comparison_highlights_both_directions(self):
        baseline = {"run_id": "a", "metrics": {"manual_agreement_rate": {"rate": 0.5}, "unavailable_field_rate": {"rate": 0.1}}}
        candidate = {"run_id": "b", "metrics": {"manual_agreement_rate": {"rate": 0.75}, "unavailable_field_rate": {"rate": 0.2}}}
        comparison = compare_runs(baseline, candidate)
        self.assertEqual(comparison["improvements"][0]["metric"], "manual_agreement_rate")
        self.assertEqual(comparison["regressions"][0]["metric"], "unavailable_field_rate")

    @patch("ui.evaluation.st")
    def test_dashboard_renders_empty_and_populated_artifacts(self, st):
        st.expander.return_value.__enter__.return_value = None
        st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        with tempfile.TemporaryDirectory() as directory:
            dataset_path = Path(directory) / "dataset.json"
            output = Path(directory) / "artifacts"
            EvaluationDatasetStore(dataset_path).save("suite", [])
            render_evaluation_dashboard(dataset_path, output)
            st.info.assert_called_with("No evaluation runs are stored yet.")
            runs = output / "runs"
            runs.mkdir(parents=True)
            payload = {"run_id": "run-a", "created_at": "now", "dataset_name": "suite", "metrics": {"observation_coverage": {"numerator": 1, "denominator": 1, "rate": 1.0}}, "failure_analysis": {}, "results": []}
            (runs / "run-a.json").write_text(json.dumps(payload), encoding="utf-8")
            render_evaluation_dashboard(dataset_path, output)
            self.assertEqual(st.download_button.call_count, 3)

    @patch("ui.advanced.render_evaluation_dashboard")
    @patch("ui.advanced.st")
    def test_builder_integration_is_hidden_from_creator(self, st, dashboard):
        st.expander.return_value.__enter__.return_value = None
        from ui.advanced import render_advanced_analysis
        render_advanced_analysis({}, "creator", {})
        dashboard.assert_not_called()
        render_advanced_analysis({}, "builder", {})
        dashboard.assert_called_once()


if __name__ == "__main__":
    unittest.main()
