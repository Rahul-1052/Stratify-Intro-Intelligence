import json
import unittest

from core.creator_report import build_creator_report
from core.observers.semantic_observer import observe_semantics
from core.reasoning.creative_reasoning import build_creative_reasoning


def frame(timestamp, focus=None, people=0, text=False, scene="", motion="held", composition=""):
    item = {
        "timestamp": timestamp, "text_overlay": text, "scene_type": scene,
        "motion_state": motion, "composition_state": composition or scene,
        "person_count": people, "human_presence": people > 0,
    }
    if focus:
        item["dominant_focus"] = focus
    return item


class ObservationSemanticsV2Tests(unittest.TestCase):
    def test_metadata_is_separate_and_title_never_becomes_visual_subject(self):
        title = "Lucy Calls Professor Norman — Full Movie Scene Official HD"
        semantic = observe_semantics(
            [frame(0, people=1, scene="person"), frame(1, people=1, scene="person")],
            metadata_context={"title": title, "description": "Metadata only"},
        )
        self.assertEqual(semantic["metadata_context"]["title"], title)
        direct = json.dumps({key: value for key, value in semantic.items() if key != "metadata_context"})
        self.assertNotIn(title, direct)
        report = {"semantic_observation": semantic, "benchmark": {}, "patterns": {}}
        creator = json.dumps(build_creator_report(report)).lower()
        self.assertNotIn(title.lower(), creator)
        self.assertNotIn("lucy", creator)

    def test_similar_frames_group_and_meaningful_change_splits_beats(self):
        frames = [
            frame(0, people=1, text=False, scene="person", motion="held", composition="close"),
            frame(1, people=1, text=False, scene="person", motion="held", composition="close"),
            frame(2, people=1, text=False, scene="person", motion="held", composition="close"),
            frame(3, people=1, text=True, scene="person", motion="held", composition="close"),
            frame(4, people=1, text=True, scene="person", motion="held", composition="close"),
        ]
        semantic = observe_semantics(frames)
        self.assertEqual(len(semantic["beats"]), 2)
        self.assertEqual(semantic["beats"][0]["supporting_frames"], [0, 1, 2])
        self.assertEqual(semantic["beats"][1]["supporting_frames"], [3, 4])

    def test_focus_clarity_is_deterministic(self):
        immediate = observe_semantics([frame(i, people=1, scene="person") for i in range(4)])
        develops = observe_semantics([
            frame(0, focus="environment", scene="room"),
            frame(1, people=1, scene="person"), frame(2, people=1, scene="person"),
        ])
        competing = observe_semantics([frame(i, people=2, scene="person") for i in range(4)])
        self.assertEqual(immediate["focus_clarity"], "immediate")
        self.assertEqual(develops["focus_clarity"], "develops_early")
        self.assertEqual(competing["focus_clarity"], "competing")
        self.assertEqual(competing["primary_visual_focus"], "multiple_people")

    def test_persistent_and_intermittent_text_are_distinct(self):
        persistent = observe_semantics([frame(i, people=1, text=True, scene="person") for i in range(4)])
        intermittent = observe_semantics([frame(0, people=1, scene="person"), frame(1, people=1, text=True, scene="person"), frame(2, people=1, scene="person")])
        self.assertEqual(persistent["text_role"], "persistent")
        self.assertEqual(intermittent["text_role"], "intermittent")

    def test_missing_evidence_returns_unavailable_semantics(self):
        semantic = observe_semantics([])
        self.assertEqual(semantic["primary_visual_focus"], "unavailable")
        self.assertEqual(semantic["focus_clarity"], "unavailable")
        self.assertEqual(semantic["visual_progression"], "unavailable")
        self.assertEqual(semantic["beats"], [])
        self.assertEqual(semantic["semantic_confidence"], "limited")

    def test_five_required_opening_patterns(self):
        patterns = {
            "dominant_person_persistent_text": [frame(i, people=1, text=True, scene="person", composition="close") for i in range(5)],
            "multiple_people": [frame(i, people=2, scene="person", composition="wide") for i in range(5)],
            "environment_first": [frame(0, focus="environment", scene="room"), frame(1, focus="environment", scene="room"), frame(2, people=1, scene="person")],
            "static": [frame(i, focus="object", scene="desk", composition="locked") for i in range(5)],
            "rapid_beats": [frame(0, focus="environment", scene="room"), frame(1, people=1, scene="person"), frame(2, focus="object", scene="desk"), frame(3, focus="text", text=True, scene="text")],
        }
        results = {name: observe_semantics(frames) for name, frames in patterns.items()}
        self.assertEqual(results["dominant_person_persistent_text"]["text_role"], "persistent")
        self.assertEqual(results["multiple_people"]["focus_clarity"], "competing")
        self.assertEqual(results["environment_first"]["opening_mode"], "environment_first")
        self.assertEqual(results["static"]["visual_progression"], "mostly_held")
        self.assertEqual(results["rapid_beats"]["visual_progression"], "frequent_change")

    def test_creator_output_uses_semantics_and_builder_raw_frames_survive(self):
        raw = [frame(0, people=1, scene="person"), frame(1, people=1, text=True, scene="person")]
        semantic = observe_semantics(raw)
        report = {"vision": {"frame_observations": raw}, "semantic_observation": semantic, "benchmark": {}, "patterns": {}}
        reasoning = build_creative_reasoning(report)
        creator = build_creator_report(report, reasoning)
        creator_text = json.dumps(creator).lower()
        prohibited = (
            "the title promises", "a changing visual sequence creates the initial attention",
            "the setting or composition shifts", "observed pacing", "observed opening",
            "person detected", "text detected", "balanced lighting", "moderate energy",
            "high energy", "move the clearest expression of that hook", "state the destination",
            "video's destination",
        )
        for phrase in prohibited:
            self.assertNotIn(phrase, creator_text)
        self.assertEqual(report["vision"]["frame_observations"], raw)
        self.assertTrue(all(item["evidence_key"] for item in reasoning["experiments"]))
        self.assertFalse(any("hook" in item["recommendation"].lower() for item in reasoning["experiments"]))


if __name__ == "__main__":
    unittest.main()
