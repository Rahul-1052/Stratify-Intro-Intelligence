import unittest

import cv2
import numpy as np

from core.beta.synthetic_clips import render_frame
from core.intelligence_v3 import build_intelligence_v3
from core.vision_analyzer import (
    _analyze_single_frame, _focal_structure, _smooth_text_presence,
    _text_region_evidence, _visual_change_signals,
)


FPS = 12
TIMES = (0, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9)


def analyze_case(case_id):
    observations, previous = [], None
    for timestamp in TIMES:
        frame = render_frame(case_id, int(timestamp * FPS), FPS)
        item, previous = _analyze_single_frame(
            frame, "fixture.jpg", timestamp, previous
        )
        observations.append(item)
    _smooth_text_presence(observations)
    return observations, build_intelligence_v3(observations)


class SceneCalibrationTests(unittest.TestCase):
    def test_rapid_montage_detects_multiple_cuts(self):
        _, result = analyze_case("gd-002-rapid-montage")
        self.assertGreaterEqual(result["visual_change_timing"]["scene_change_count"], 5)

    def test_frequent_scenes_remain_frequent(self):
        _, result = analyze_case("gd-007-frequent-scenes")
        self.assertGreaterEqual(result["visual_change_timing"]["scene_change_count"], 5)

    def test_no_scene_clip_remains_stable(self):
        _, result = analyze_case("gd-008-no-scenes")
        self.assertEqual(result["visual_change_timing"]["scene_change_count"], 0)
        self.assertGreaterEqual(result["visual_change_timing"]["scene_continuity"], 0.9)

    def test_talking_head_does_not_gain_false_cuts(self):
        _, result = analyze_case("gd-001-static-talking-head")
        self.assertEqual(result["visual_change_timing"]["scene_change_count"], 0)

    def test_near_identical_frames_do_not_cut(self):
        first = np.full((180, 320, 3), 80, dtype=np.uint8)
        second = first.copy()
        cv2.circle(second, (160, 90), 2, (82, 82, 82), -1)
        self.assertFalse(_visual_change_signals(second, first)["scene_cut_detected"])

    def test_event_merging_keeps_one_scene_cut_per_timestamp(self):
        observations, result = analyze_case("gd-002-rapid-montage")
        timestamps = [
            item["timestamp"] for item in result["meaningful_change_events"]
            if item["event_type"] == "scene_change"
        ]
        self.assertEqual(len(timestamps), len(set(timestamps)))
        self.assertTrue(any(item["scene_cut_detected"] for item in observations[1:]))

    def test_continuity_decreases_with_cut_frequency(self):
        _, static = analyze_case("gd-008-no-scenes")
        _, montage = analyze_case("gd-002-rapid-montage")
        self.assertGreater(
            static["visual_change_timing"]["scene_continuity"],
            montage["visual_change_timing"]["scene_continuity"],
        )

    def test_novelty_rises_with_visual_variation(self):
        _, static = analyze_case("gd-008-no-scenes")
        _, montage = analyze_case("gd-002-rapid-montage")
        self.assertGreater(
            montage["visual_novelty"]["average"],
            static["visual_novelty"]["average"],
        )


class TextCalibrationTests(unittest.TestCase):
    def test_early_text_detected_in_first_second(self):
        observations, _ = analyze_case("gd-005-early-text")
        timestamps = [item["timestamp"] for item in observations if item["text_overlay"]]
        self.assertLessEqual(min(timestamps), 1.0)

    def test_late_text_follows_initial_absence(self):
        observations, _ = analyze_case("gd-006-late-text")
        timestamps = [item["timestamp"] for item in observations if item["text_overlay"]]
        self.assertFalse(observations[0]["text_overlay"])
        self.assertGreaterEqual(min(timestamps), 4.0)

    def test_no_text_clip_remains_negative(self):
        observations, _ = analyze_case("gd-001-static-talking-head")
        self.assertFalse(any(item["text_overlay"] for item in observations))

    def test_persistent_text_has_nonzero_ratio(self):
        observations, _ = analyze_case("gd-005-early-text")
        ratio = sum(item["text_overlay"] for item in observations) / len(observations)
        self.assertGreater(ratio, 0.1)

    def test_isolated_noise_is_smoothed_out(self):
        observations = [
            {"text_overlay_raw": False, "text_overlay_score": 0,
             "text_overlay_confidence": "limited"},
            {"text_overlay_raw": True, "text_overlay_score": 0.5,
             "text_overlay_confidence": "moderate"},
            {"text_overlay_raw": False, "text_overlay_score": 0,
             "text_overlay_confidence": "limited"},
        ]
        _smooth_text_presence(observations)
        self.assertFalse(any(item["text_overlay"] for item in observations))

    def test_text_region_evidence_has_confidence_and_regions(self):
        frame = render_frame("gd-005-early-text", 0, FPS)
        evidence = _text_region_evidence(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        self.assertTrue(evidence["detected"])
        self.assertGreater(evidence["region_count"], 0)
        self.assertIn(evidence["confidence"], {"moderate", "high"})

    def test_text_timestamps_are_preserved(self):
        observations, _ = analyze_case("gd-006-late-text")
        self.assertEqual(
            [item["timestamp"] for item in observations if item["text_overlay"]][0],
            5,
        )


class FocalCalibrationTests(unittest.TestCase):
    def test_stable_central_anchor_is_stable(self):
        _, result = analyze_case("gd-009-stable-anchor")
        density = result["visual_density"]
        self.assertEqual(density["focal_stability"], "stable")
        self.assertEqual(
            density["classification"], "high_density_stable_focal_anchor"
        )

    def test_peripheral_motion_does_not_create_competition(self):
        _, result = analyze_case("gd-009-stable-anchor")
        self.assertLess(result["visual_density"]["focal_competition_score"], 0.52)

    def test_similarly_prominent_regions_create_competition(self):
        _, result = analyze_case("gd-010-competing-focal")
        self.assertGreaterEqual(
            result["visual_density"]["focal_competition_score"], 0.52
        )
        self.assertEqual(
            result["visual_density"]["classification"],
            "high_density_competing_focal_regions",
        )

    def test_top_region_dominance_reduces_competition(self):
        frame = np.full((360, 640, 3), (40, 50, 60), dtype=np.uint8)
        cv2.circle(frame, (250, 180), 100, (40, 220, 240), -1)
        cv2.circle(frame, (540, 180), 28, (220, 80, 160), -1)
        result = _focal_structure(frame)
        self.assertGreater(result["focal_dominance_score"], 0.7)
        self.assertLess(result["focal_competition_score"], 0.52)

    def test_visible_element_count_is_reasonable(self):
        _, result = analyze_case("gd-010-competing-focal")
        self.assertGreaterEqual(result["visual_density"]["average_visible_elements"], 2)
        self.assertLess(result["visual_density"]["average_visible_elements"], 6)

    def test_centroid_drift_maps_to_stability(self):
        _, stable = analyze_case("gd-009-stable-anchor")
        _, moving = analyze_case("gd-010-competing-focal")
        self.assertLess(
            stable["visual_density"]["focal_centroid_drift"],
            moving["visual_density"]["focal_centroid_drift"],
        )


class ProtectedRegressionTests(unittest.TestCase):
    def test_existing_static_and_subject_strengths_remain(self):
        observations, static = analyze_case("gd-001-static-talking-head")
        self.assertEqual(observations[0]["visual_energy"], "low")
        self.assertEqual(static["visual_change_timing"]["change_count"], 0)
        self.assertEqual(static["subject_continuity"], "stable_visible_subject")

        _, early = analyze_case("gd-003-early-subject")
        self.assertEqual(early["subject_continuity"], "stable_visible_subject")

    def test_delayed_subject_and_information_remain_detected(self):
        observations, result = analyze_case("gd-004-delayed-subject")
        self.assertFalse(observations[0]["human_presence"])
        self.assertEqual(result["subject_continuity"], "subject_introduced_later")
        self.assertGreaterEqual(
            result["information_introduction"]["time_to_first_event"], 3
        )


if __name__ == "__main__":
    unittest.main()
