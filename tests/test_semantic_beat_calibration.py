import json
import unittest

from core.creator_report import build_creator_report
from core.observers.semantic_observer import observe_semantics
from core.reasoning.creative_reasoning import build_creative_reasoning


def frame(index, focus="person", composition="medium", environment="set-a", text=False, motion="held"):
    return {
        "timestamp": index,
        "dominant_focus": focus,
        "composition_state": composition,
        "environment": environment,
        "text_overlay": text,
        "motion_state": motion,
        "human_presence": focus in {"person", "multiple_people"},
        "person_count": 2 if focus == "multiple_people" else 1 if focus == "person" else 0,
    }


class SemanticBeatCalibrationTests(unittest.TestCase):
    def test_alternating_subject_views_merge_into_one_semantic_beat(self):
        frames = [frame(i, composition="a" if i % 2 == 0 else "b") for i in range(8)]
        semantic = observe_semantics(frames)
        self.assertEqual(len(semantic["beats"]), 1)
        self.assertEqual(semantic["beats"][0]["beat_purpose"], "multi_subject_sequence")
        self.assertEqual(semantic["primary_visual_focus"], "alternating_subjects")
        self.assertTrue(semantic["temporal_diagnostics"]["alternating_patterns"])

    def test_environment_to_subject_is_a_persistent_semantic_change(self):
        frames = [frame(0, "environment", "wide"), frame(1, "environment", "wide"), frame(2, "person", "medium"), frame(3, "person", "close")]
        semantic = observe_semantics(frames)
        self.assertEqual([beat["beat_purpose"] for beat in semantic["beats"]], ["environment_setup", "subject_establishment"])

    def test_wide_to_close_same_subject_is_not_a_new_semantic_beat(self):
        semantic = observe_semantics([frame(0, composition="wide"), frame(1, composition="wide"), frame(2, composition="close"), frame(3, composition="close")])
        self.assertEqual(len(semantic["beats"]), 1)
        self.assertGreater(len(semantic["temporal_diagnostics"]["candidate_visual_state_boundaries"]), 1)

    def test_brief_text_does_not_split_but_persistent_text_change_does(self):
        brief = observe_semantics([frame(0), frame(1, text=True), frame(2), frame(3)])
        persistent = observe_semantics([frame(0), frame(1), frame(2, text=True), frame(3, text=True)])
        self.assertEqual(len(brief["beats"]), 1)
        self.assertEqual(len(persistent["beats"]), 2)

    def test_isolated_motion_does_not_split_stable_sequence(self):
        semantic = observe_semantics([frame(0), frame(1), frame(2, motion="active"), frame(3), frame(4)])
        self.assertEqual(len(semantic["beats"]), 1)
        self.assertIn("isolated_motion_change", semantic["temporal_diagnostics"]["merge_reasons"])

    def test_sustained_new_visual_function_creates_a_beat(self):
        semantic = observe_semantics([
            frame(0, "object", "locked", motion="held"), frame(1, "object", "locked", motion="held"),
            frame(2, "object", "active", motion="active"), frame(3, "object", "active", motion="active"),
        ])
        self.assertEqual([beat["beat_purpose"] for beat in semantic["beats"]], ["composition_hold", "active_demonstration"])

    def test_fifteen_second_edited_scene_is_calibrated_and_descriptions_are_unique(self):
        frames = [frame(i, composition=("wide", "close", "side")[i % 3]) for i in range(15)]
        semantic = observe_semantics(frames)
        descriptions = [beat["semantic_description"] for beat in semantic["beats"]]
        self.assertLessEqual(len(descriptions), 5)
        self.assertEqual(len(descriptions), len(set(descriptions)))
        self.assertGreater(len(semantic["temporal_diagnostics"]["candidate_frame_changes"]), len(descriptions))

    def test_creator_uses_final_beats_and_builder_retains_all_levels(self):
        frames = [frame(i, composition="a" if i % 2 == 0 else "b") for i in range(6)]
        semantic = observe_semantics(frames)
        report = {"semantic_observation": semantic, "vision": {"frame_observations": frames}, "benchmark": {}, "patterns": {}}
        reasoning = build_creative_reasoning(report)
        creator = build_creator_report(report, reasoning)
        self.assertEqual(len(creator["intro_timeline"]), len(semantic["beats"]))
        diagnostics = semantic["temporal_diagnostics"]
        for key in ("candidate_frame_changes", "candidate_visual_state_boundaries", "final_semantic_boundaries", "merge_decisions", "persistence_thresholds", "rejected_split_candidates"):
            self.assertIn(key, diagnostics)
        self.assertEqual(report["vision"]["frame_observations"], frames)

    def test_experiments_are_semantic_and_internally_consistent(self):
        frames = [frame(i, composition="a" if i % 2 == 0 else "b") for i in range(6)]
        semantic = observe_semantics(frames)
        reasoning = build_creative_reasoning({"semantic_observation": semantic})
        experiments = reasoning["experiments"]
        payload = json.dumps(experiments).lower()
        self.assertNotIn("the second beat", payload)
        self.assertNotIn("move the start of the second beat", payload)
        self.assertTrue(all(item["evidence_key"] for item in experiments))
        self.assertTrue(all(item["beat_references"] for item in experiments))
        self.assertTrue(all(item["beat_references"][0]["beat_purpose"] == "multi_subject_sequence" for item in experiments))
        for item in experiments:
            if "order" in item["recommendation"].lower() or "move" in item["recommendation"].lower():
                self.assertNotIn("order unchanged", item["what_stays_constant"].lower())

    def test_six_required_semantic_patterns(self):
        patterns = {
            "shot_reverse_shot": [frame(i, composition="a" if i % 2 == 0 else "b") for i in range(8)],
            "one_person_closeups": [frame(i, composition="close" if i % 2 else "medium") for i in range(6)],
            "environment_reveal": [frame(0, "environment"), frame(1, "environment"), frame(2, "person"), frame(3, "person")],
            "persistent_text": [frame(i, text=True) for i in range(6)],
            "purpose_montage": [frame(0, "environment"), frame(1, "person"), frame(2, "text", text=True), frame(3, "object", motion="active")],
            "static_setup": [frame(i) for i in range(6)],
        }
        results = {name: observe_semantics(value) for name, value in patterns.items()}
        self.assertEqual(len(results["shot_reverse_shot"]["beats"]), 1)
        self.assertEqual(len(results["one_person_closeups"]["beats"]), 1)
        self.assertEqual(len(results["environment_reveal"]["beats"]), 2)
        self.assertEqual(results["persistent_text"]["text_role"], "persistent")
        self.assertGreaterEqual(len(results["purpose_montage"]["beats"]), 3)
        self.assertEqual(len(results["static_setup"]["beats"]), 1)


if __name__ == "__main__":
    unittest.main()
