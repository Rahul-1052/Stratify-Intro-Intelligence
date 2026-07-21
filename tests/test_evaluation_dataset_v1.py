import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from core.evaluation.dataset import EvaluationDatasetStore
from core.evaluation.dataset_validation import (
    REQUIRED_COMPLETE_FIELDS,
    V1_CATEGORIES,
    dataset_readiness,
    validate_dataset,
)
from core.evaluation.evaluation_models import EvaluationVideo


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "evaluation_data" / "dataset.json"


def complete_labels():
    return {
        "primary_visual_focus": "person",
        "focus_clarity": "immediate",
        "opening_mode": "subject_first",
        "visual_progression": "mostly_held",
        "text_role": "absent",
        "number_of_semantic_beats": 1,
        "best_strength": "One visible subject remains clear.",
        "largest_weakness": "unavailable",
        "expected_experiment": [],
        "manual_confidence": "moderate",
    }


class EvaluationDatasetV1Tests(unittest.TestCase):
    def test_real_dataset_has_fifteen_balanced_unreviewed_entries(self):
        dataset = EvaluationDatasetStore(DATASET_PATH).load()
        self.assertEqual(len(dataset["videos"]), 15)
        self.assertEqual(Counter(video.category for video in dataset["videos"]), Counter({category: 3 for category in V1_CATEGORIES}))
        self.assertEqual(len({video.evaluation_id for video in dataset["videos"]}), 15)
        self.assertEqual(len({video.video_id for video in dataset["videos"]}), 15)
        self.assertTrue(all(video.status == "unreviewed" for video in dataset["videos"]))
        self.assertTrue(all(video.expected_manual_labels == {} for video in dataset["videos"]))
        self.assertEqual(validate_dataset(dataset), [])

    def test_unreviewed_partial_and_complete_states(self):
        videos = [
            EvaluationVideo("a", "A", "offline", "test", "fixture://a", {}, status="unreviewed", evaluation_id="a"),
            EvaluationVideo("b", "B", "offline", "test", "fixture://b", {"text_role": "uncertain"}, status="partial", evaluation_id="b"),
            EvaluationVideo("c", "C", "offline", "test", "fixture://c", complete_labels(), status="complete", evaluation_id="c"),
        ]
        self.assertEqual(validate_dataset({"name": "states", "videos": videos}, require_v1_shape=False), [])
        self.assertTrue(set(REQUIRED_COMPLETE_FIELDS).issubset(videos[2].expected_manual_labels))

    def test_invalid_controlled_label_and_incomplete_complete_review(self):
        bad = EvaluationVideo("bad", "Bad", "offline", "test", "fixture://bad", {"focus_clarity": "title_says_exciting"}, status="partial", evaluation_id="bad")
        errors = validate_dataset({"name": "bad", "videos": [bad]}, require_v1_shape=False)
        self.assertTrue(any("invalid focus_clarity" in error for error in errors))
        bad.status = "complete"
        errors = validate_dataset({"name": "bad", "videos": [bad]}, require_v1_shape=False)
        self.assertTrue(any("missing required fields" in error for error in errors))

    def test_save_manual_label_preserves_unrelated_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.json"
            payload = {
                "name": "preservation", "custom_top_level": {"owner": "Rahul"},
                "videos": [{
                    "evaluation_id": "eval-1", "video_id": "v1", "video_title": "Original metadata title",
                    "source": "offline", "category": "test", "url": "fixture://v1",
                    "expected_manual_labels": {}, "status": "unreviewed", "evaluation_history": [],
                    "custom_entry_field": "preserve-me",
                }],
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            store = EvaluationDatasetStore(path)
            store.save_manual_review("eval-1", {"text_role": "intermittent"}, "partial", "Reviewed opening only.")
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["custom_top_level"], {"owner": "Rahul"})
            self.assertEqual(saved["videos"][0]["custom_entry_field"], "preserve-me")
            self.assertEqual(saved["videos"][0]["expected_manual_labels"], {"text_role": "intermittent"})
            self.assertEqual(saved["videos"][0]["status"], "partial")

    def test_review_state_transitions_and_metadata_independence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.json"
            store = EvaluationDatasetStore(path)
            video = EvaluationVideo("v1", "Metadata title A", "offline", "test", "fixture://v1", {}, status="unreviewed", evaluation_id="eval-1")
            store.save("transitions", [video])
            store.save_manual_review("eval-1", {}, "incomplete")
            store.save_manual_review("eval-1", {"text_role": "uncertain"}, "partial")
            labels_before = store.load()["videos"][0].expected_manual_labels
            dataset = store.load()
            dataset["videos"][0].video_title = "Completely different metadata title"
            store.save(dataset["name"], dataset["videos"])
            self.assertEqual(store.load()["videos"][0].expected_manual_labels, labels_before)
            store.save_manual_review("eval-1", complete_labels(), "complete")
            self.assertEqual(store.load()["videos"][0].status, "complete")

    def test_baseline_readiness_requires_all_complete(self):
        dataset = EvaluationDatasetStore(DATASET_PATH).load()
        readiness = dataset_readiness(dataset)
        self.assertEqual(readiness["total_entries"], 15)
        self.assertEqual(readiness["unreviewed_entries"], 15)
        self.assertEqual(readiness["completion_percentage"], 0.0)
        self.assertFalse(readiness["baseline_v1_ready"])
        for video in dataset["videos"]:
            video.status = "complete"
            video.expected_manual_labels = complete_labels()
        readiness = dataset_readiness(dataset)
        self.assertEqual(readiness["completion_percentage"], 100.0)
        self.assertTrue(readiness["baseline_v1_ready"])

    def test_evaluation_categories_are_not_imported_by_production_reasoning(self):
        production = [
            ROOT / "core" / "reasoning" / "creative_reasoning.py",
            ROOT / "core" / "creator_report.py",
            ROOT / "core" / "stratify_report.py",
            ROOT / "core" / "observers" / "semantic_observer.py",
        ]
        self.assertTrue(all("V1_CATEGORIES" not in path.read_text(encoding="utf-8") for path in production))

    @patch("ui.advanced.render_evaluation_dashboard")
    @patch("ui.advanced.st")
    def test_creator_mode_isolated_from_labeling_interface(self, st, dashboard):
        st.expander.return_value.__enter__.return_value = None
        from ui.advanced import render_advanced_analysis
        render_advanced_analysis({}, "creator", {})
        dashboard.assert_not_called()

    def test_builder_labeling_interface_renders_all_entries(self):
        from streamlit.testing.v1 import AppTest
        from tests.test_streamlit_workspace import _project_with_observation_report
        app = AppTest.from_file("app.py")
        app.session_state["stratify_project"] = _project_with_observation_report()
        app.run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        selector = next(item for item in app.selectbox if item.label == "Dataset entry")
        self.assertEqual(len(selector.options), 15)
        self.assertTrue(any(item.label == "Review status" for item in app.selectbox))
        self.assertTrue(any(item.label == "Save manual review" for item in app.button))


if __name__ == "__main__":
    unittest.main()
