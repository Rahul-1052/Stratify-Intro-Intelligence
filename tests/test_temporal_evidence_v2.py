import unittest

from core.observers.temporal_evidence import build_temporal_evidence
from utils.frame_extractor import SamplingConfig, build_sampling_timestamps


class AdaptiveSamplingTests(unittest.TestCase):
    def test_sampling_is_denser_early_unique_and_bounded(self):
        values = build_sampling_timestamps(15)
        self.assertEqual(values[:7], [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
        self.assertLessEqual(len(values), 20)
        self.assertEqual(len(values), len(set(values)))

    def test_short_clip_and_custom_bound(self):
        self.assertEqual(build_sampling_timestamps(0.2), [0.0])
        self.assertEqual(len(build_sampling_timestamps(15, SamplingConfig(maximum_samples=3))), 3)


class TemporalEvidenceTests(unittest.TestCase):
    @staticmethod
    def frame(timestamp, text=False, people=0, motion=0):
        return {"timestamp": timestamp, "text_overlay": text, "text_overlay_confidence": "limited",
                "human_presence": people > 0, "subject_count": people, "motion_score": motion}

    def test_isolated_text_is_limited_and_rejected(self):
        result = build_temporal_evidence([self.frame(0), self.frame(.5, text=True), self.frame(1)])
        self.assertEqual(result["windows"][0]["persistence"], "isolated")
        self.assertEqual(result["windows"][0]["confidence"], "limited")
        self.assertEqual(result["rejected_isolated_evidence"][0]["reason"], "isolated_detection")

    def test_persistent_text_and_subject_windows_preserve_time(self):
        result = build_temporal_evidence([self.frame(0, True, 1), self.frame(.5, True, 1), self.frame(1, True, 1), self.frame(2)])
        windows = {item["evidence_type"]: item for item in result["windows"]}
        self.assertEqual(windows["text_like"]["persistence"], "persistent")
        self.assertEqual(windows["subject_presence"]["end_time"], 1.5)

    def test_multiple_subject_and_transition_states(self):
        result = build_temporal_evidence([self.frame(0, people=2), self.frame(.5, people=2, motion=10), self.frame(1, motion=20)])
        windows = {item["evidence_type"]: item for item in result["windows"]}
        self.assertEqual(windows["multiple_subjects"]["persistence"], "persistent")
        self.assertEqual(windows["transition_activity"]["persistence"], "rapid")

    def test_empty_evidence_abstains(self):
        result = build_temporal_evidence([])
        self.assertEqual(result["windows"], [])
        self.assertIn("No frame", result["confidence_reasons"][0])


if __name__ == "__main__":
    unittest.main()
