import unittest
from unittest.mock import patch

import numpy as np

from core.creator_report import build_creator_report
from core.observers.semantic_observer import observe_semantics
from core.reasoning.creative_reasoning import build_creative_reasoning
from core.understanding import understand_creative_opening
from core.vision_analyzer import _analyze_single_frame, _count_prominent_faces


def frame(timestamp, focus="environment", text=False, motion=0):
    value = {"timestamp": timestamp, "text_overlay": text, "motion_score": motion}
    if focus == "person":
        value.update(human_presence=True, scene_type="person_focused")
    elif focus == "object":
        value.update(object_presence=True, scene_type="object")
    elif focus == "text":
        value.update(scene_type="text_led")
    else:
        value.update(scene_type="environment")
    return value


def analyzed(frames):
    semantic = observe_semantics(frames)
    structure, understanding = understand_creative_opening(semantic)
    report = {
        "semantic_observation": semantic,
        "creative_structure": structure.to_dict(),
        "creative_understanding": understanding.to_dict(),
        "benchmark": {}, "patterns": {},
    }
    reasoning = build_creative_reasoning(report)
    return semantic, structure, understanding, reasoning, build_creator_report(report, reasoning)


class RealWorldCalibrationTests(unittest.TestCase):
    def test_multiple_subjects_require_consecutive_persistence(self):
        isolated = [frame(index, "person") for index in range(5)]
        isolated[1]["subject_count"] = 2
        isolated[3]["subject_count"] = 2
        self.assertEqual(observe_semantics(isolated)["primary_visual_focus"], "person")

        persistent = [frame(index, "person") for index in range(5)]
        persistent[1]["subject_count"] = 2
        persistent[2]["subject_count"] = 2
        self.assertEqual(observe_semantics(persistent)["primary_visual_focus"], "multiple_people")

    def test_face_count_deduplicates_overlap_and_ignores_small_false_positives(self):
        self.assertEqual(_count_prominent_faces([(10, 10, 300, 300), (40, 30, 250, 250)]), 1)
        self.assertEqual(_count_prominent_faces([(10, 10, 250, 250), (300, 10, 230, 230), (0, 0, 50, 50)]), 2)

    @patch("core.vision_analyzer._detect_text_like_regions", return_value=True)
    @patch("core.vision_analyzer._detect_human_count", return_value=3)
    def test_frame_observation_preserves_detected_subject_count_and_text_limit(self, human_count, text):
        observation, _ = _analyze_single_frame(
            np.zeros((120, 160, 3), dtype=np.uint8), "fixture.jpg", 0.0, None
        )
        self.assertTrue(observation["human_presence"])
        self.assertEqual(observation["subject_count"], 3)
        self.assertEqual(observation["text_overlay_confidence"], "limited")

    def test_limited_text_detector_confidence_propagates_to_advice(self):
        frames = [
            {**frame(index, "person", text=True), "text_overlay_confidence": "limited"}
            for index in range(4)
        ]
        semantic, _, understanding, reasoning, _ = analyzed(frames)
        self.assertEqual(semantic["text_evidence_confidence"], "limited")
        self.assertIn("possible written information", understanding.summary)
        text_experiments = [
            item for item in reasoning["experiments"]
            if item["structural_dimension"] in {"information_density", "information_order"}
        ]
        self.assertTrue(text_experiments)
        self.assertTrue(all(item["confidence"] == "limited" for item in text_experiments))
        self.assertTrue(all(item["limitations"] for item in text_experiments))

    def test_active_openings_are_classified_by_change_not_anchor_type(self):
        for focus in ("person", "object", "environment"):
            with self.subTest(focus=focus):
                semantic, structure, _, _, _ = analyzed([frame(index, focus, motion=24) for index in range(4)])
                self.assertEqual(semantic["opening_mode"], "action_or_change_first")
                self.assertEqual(structure.opening_strategy, "change-first")

    def test_late_context_to_anchor_handoffs_identify_the_revealed_anchor(self):
        for focus, expected in (("person", "single subject"), ("object", "object")):
            with self.subTest(focus=focus):
                frames = [frame(index) for index in range(3)] + [frame(3, focus), frame(4, focus)]
                _, structure, understanding, reasoning, _ = analyzed(frames)
                self.assertEqual(structure.visual_anchor, expected)
                self.assertEqual(structure.reveal_pattern, "anchor revealed later")
                self.assertIn(expected, understanding.summary)
                self.assertEqual(reasoning["priority"]["structural_dimension"], "reveal_timing")

    def test_summary_includes_material_information_density_difference(self):
        sparse = analyzed([frame(index, "person") for index in range(4)])[2].summary
        dense = analyzed([frame(index, "person", text=True) for index in range(4)])[2].summary
        intermittent = analyzed([
            frame(0, "person"), frame(1, "person", text=True),
            frame(2, "person", text=True), frame(3, "person"),
        ])[2].summary
        self.assertEqual(len({sparse, dense, intermittent}), 3)
        self.assertIn("without written information", sparse)
        self.assertIn("layered continuously", dense)
        self.assertIn("selected moments", intermittent)
        for summary in (sparse, dense, intermittent):
            self.assertNotIn("then anchor", summary)

    def test_readable_no_signal_is_not_reported_as_missing_evidence(self):
        _, _, _, reasoning, creator = analyzed([frame(index, "person") for index in range(4)])
        self.assertEqual(reasoning["status"], "success")
        self.assertIsNone(reasoning["priority"])
        self.assertEqual(creator["biggest_opportunity"]["title"], "No supported structural change yet")
        self.assertEqual(creator["experiments"], [])

        unknown = build_creator_report({})
        self.assertEqual(unknown["biggest_opportunity"]["title"], "Gather a clearer opening sample")

    def test_every_calibrated_experiment_retains_control_fields(self):
        _, _, _, reasoning, _ = analyzed([
            frame(0, "text", text=True), frame(1, "text", text=True),
            frame(2, "person", text=True), frame(3, "person"),
        ])
        self.assertTrue(reasoning["experiments"])
        dimensions = [item["structural_dimension"] for item in reasoning["experiments"]]
        self.assertEqual(len(dimensions), len(set(dimensions)))
        for experiment in reasoning["experiments"]:
            self.assertTrue(experiment["recommendation"])
            self.assertTrue(experiment["what_stays_constant"])
            self.assertTrue(experiment["how_to_compare"])
            self.assertTrue(experiment["confidence"])
            self.assertIn("limitations", experiment)


if __name__ == "__main__":
    unittest.main()
