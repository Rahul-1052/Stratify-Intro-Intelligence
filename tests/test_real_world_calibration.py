import unittest

from core.creator_report import build_creator_report
from core.observers.semantic_observer import observe_semantics
from core.reasoning.creative_reasoning import build_creative_reasoning
from core.understanding import understand_creative_opening


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
