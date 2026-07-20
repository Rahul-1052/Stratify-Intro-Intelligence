import json
import unittest

from core.creator_report import build_creator_report
from core.reasoning.creative_reasoning import build_creative_reasoning


BANNED_CREATOR_PHRASES = (
    "observed pacing", "observed opening", "visual changes", "moderate energy",
    "balanced lighting", "person detected", "text detected",
)


def fixture(subject, hook, promise, scenes, text=False):
    frames = []
    for index, scene in enumerate(scenes):
        frames.append({
            "timestamp": index * 2,
            "scene_type": scene,
            "visual_energy": "high" if index else "moderate",
            "human_presence": index == 0,
            "text_overlay": text and index == 1,
        })
    return {
        "intro_observation": {"status": "success", "observation": {
            "main_subject": subject, "hook_type": hook, "story_promise": promise,
        }},
        "feature_report": {"feature_summary": {}},
        "vision": {"frame_observations": frames},
        "benchmark": {}, "patterns": {},
    }


class CreativeReasoningTests(unittest.TestCase):
    def test_five_video_styles_produce_complete_grounded_reasoning(self):
        reports = (
            fixture("a cook preparing one dish", "a finished result shown before the process", "learning how the dish is made", ["kitchen", "counter"], True),
            fixture("a host speaking with a guest", "a direct question", "hearing the guest explain the central idea", ["studio", "studio"], True),
            fixture("a compact camera", "a hands-on demonstration", "seeing how the camera works in practice", ["desk", "outdoor test"]),
            fixture("a player entering a difficult level", "immediate gameplay", "seeing whether the challenge can be completed", ["game menu", "active level"]),
            fixture("an archival location", "an unanswered historical question", "understanding what happened there", ["archive", "present-day location"], True),
        )
        for report in reports:
            with self.subTest(subject=report["intro_observation"]["observation"]["main_subject"]):
                reasoning = build_creative_reasoning(report)
                creator = build_creator_report(report, reasoning)
                self.assertEqual(reasoning["status"], "success")
                self.assertGreaterEqual(len(reasoning["experiments"]), 2)
                for insight in reasoning["insights"]:
                    for key in ("observation", "interpretation", "recommendation", "reason"):
                        self.assertTrue(insight[key])
                creator_text = json.dumps(creator).lower()
                for phrase in BANNED_CREATOR_PHRASES:
                    self.assertNotIn(phrase, creator_text)

    def test_recommendations_are_traceable_to_present_evidence(self):
        report = fixture("a maker assembling a prototype", "a problem stated on camera", "seeing the prototype work", ["workbench", "test area"], True)
        reasoning = build_creative_reasoning(report)
        from core.observers.semantic_observer import observe_semantics
        semantic = observe_semantics(report["vision"]["frame_observations"])
        for item in reasoning["insights"]:
            for basis in item["evidence_key"].split(";"):
                field, value = basis.split(":", 1)
                self.assertEqual(semantic[field], value)

    def test_missing_evidence_omits_recommendations(self):
        report = {"intro_observation": {}, "feature_report": {}, "vision": {}, "benchmark": {}, "patterns": {}}
        reasoning = build_creative_reasoning(report)
        creator = build_creator_report(report, reasoning)
        self.assertEqual(reasoning["status"], "limited")
        self.assertEqual(reasoning["insights"], [])
        self.assertEqual(creator["experiments"], [])

    def test_creator_timeline_translates_technical_frames(self):
        report = fixture("a presenter", "a direct demonstration", "seeing the result", ["room", "close-up"], True)
        creator = build_creator_report(report)
        timeline = json.dumps(creator["intro_timeline"]).lower()
        for technical in ("visual_energy", "human_presence", "text_overlay", "scene_type"):
            self.assertNotIn(technical, timeline)


if __name__ == "__main__":
    unittest.main()
