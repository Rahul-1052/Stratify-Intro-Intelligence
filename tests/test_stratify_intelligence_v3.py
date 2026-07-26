import unittest

from core.creator_report import build_creator_report
from core.intelligence_v3 import (
    AVAILABILITY_STATES,
    EvidenceFinding,
    MeaningfulChangeEvent,
    build_intelligence_v3,
)
from core.product_validation.checks import run_quality_checks
from core.reasoning.creative_reasoning import build_creative_reasoning


def frame(timestamp, composition="wide", scene="room", people=1, text=False,
          motion=0, focus="person", lighting="balanced", graphics=0):
    return {
        "timestamp": timestamp, "composition_state": composition,
        "scene_type": scene, "subject_count": people,
        "human_presence": people > 0, "text_overlay": text,
        "text_overlay_confidence": "limited", "motion_score": motion,
        "dominant_focus": focus, "dominant_lighting": lighting,
        "brightness_score": {"dark": 45, "balanced": 120, "bright": 200}[lighting],
        "contrast_score": 45, "visual_energy": "moderate" if motion >= 7 else "low",
        "graphic_region_count": graphics,
    }


def report(frames, benchmark=None):
    intelligence = build_intelligence_v3(frames, benchmark)
    semantic = {
        "version": "observation-semantics-v2", "primary_visual_focus": "person",
        "focus_clarity": "immediate", "opening_mode": "subject_first",
        "visual_progression": "mostly_held", "information_mode": "image_led",
        "text_role": "absent", "subject_presence_pattern": "present_immediately",
        "semantic_confidence": "moderate",
        "supporting_evidence": [{"timestamp": item["timestamp"]} for item in frames],
        "beats": [{"start_time": 0, "end_time": len(frames),
                   "semantic_description": "One visible subject remains established.",
                   "confidence": "moderate"}],
        "opening_clarity_summary": "One visible subject remains established.",
    }
    return {
        "status": "success", "vision": {"frame_observations": frames},
        "semantic_observation": semantic, "intelligence_v3": intelligence,
        "benchmark": benchmark or {}, "patterns": {},
    }


class TemporalObservationV3Tests(unittest.TestCase):
    def test_meaningful_change_serialization(self):
        event = MeaningfulChangeEvent(2.0, "scene_change", "a", "b", "moderate")
        self.assertEqual(event.to_dict()["timestamp"], 2.0)

    def test_first_change_and_stable_interval(self):
        data = build_intelligence_v3([
            frame(0), frame(1), frame(2), frame(3, composition="close"),
            frame(4, composition="close"),
        ])
        self.assertEqual(data["visual_change_timing"]["time_to_first_change"], 3)
        self.assertEqual(data["visual_change_timing"]["longest_stable_interval"]["duration"], 3)

    def test_ordinary_noise_is_not_a_change(self):
        frames = [frame(index) for index in range(5)]
        frames[2]["brightness_score"] += 2
        self.assertEqual(build_intelligence_v3(frames)["meaningful_change_events"], [])

    def test_rapid_repeated_changes_and_cadence_intervals(self):
        frames = [frame(index, composition="a" if index % 2 else "b") for index in range(6)]
        cadence = build_intelligence_v3(frames)["visual_cadence"]
        self.assertEqual(cadence["intervals"], [1.0, 1.0, 1.0, 1.0])
        self.assertEqual(cadence["progression"], "stable")

    def test_increasing_visual_cadence(self):
        timestamps = [0, 4, 7, 9, 10]
        frames = [frame(value, composition=str(index)) for index, value in enumerate(timestamps)]
        self.assertEqual(build_intelligence_v3(frames)["visual_cadence"]["progression"], "accelerating")

    def test_decreasing_visual_cadence(self):
        timestamps = [0, 1, 3, 6, 10]
        frames = [frame(value, composition=str(index)) for index, value in enumerate(timestamps)]
        self.assertEqual(build_intelligence_v3(frames)["visual_cadence"]["progression"], "decelerating")

    def test_novelty_progression_and_near_duplicate_transitions(self):
        frames = [frame(0), frame(1, composition="close"),
                  frame(2, composition="wide"), frame(3, composition="close")]
        novelty = build_intelligence_v3(frames)["visual_novelty"]
        self.assertTrue(novelty["scores"])
        self.assertGreaterEqual(novelty["near_duplicate_transition_count"], 1)

    def test_text_introduction_early_and_late(self):
        early = build_intelligence_v3([frame(0), frame(1, text=True), frame(2, text=True)])
        late = build_intelligence_v3([frame(0), frame(1), frame(4, text=True)])
        self.assertEqual(early["information_introduction"]["time_to_first_event"], 1)
        self.assertEqual(late["information_introduction"]["time_to_first_event"], 4)

    def test_subject_continuity_states(self):
        stable = build_intelligence_v3([frame(0), frame(1), frame(2)])
        alternate = build_intelligence_v3([
            frame(0, people=1), frame(1, people=0), frame(2, people=1),
            frame(3, people=0),
        ])
        self.assertEqual(stable["subject_continuity"], "stable_visible_subject")
        self.assertEqual(alternate["subject_continuity"], "alternating_visible_subjects")

    def test_density_distinguishes_stable_and_competing_focus(self):
        stable = build_intelligence_v3([
            frame(0, people=2, text=True, focus="person"),
            frame(1, people=2, text=True, focus="person"),
        ])
        competing = build_intelligence_v3([
            frame(0, people=2, text=True, focus="person"),
            frame(1, people=2, text=True, focus="object"),
        ])
        self.assertEqual(stable["visual_density"]["classification"], "high_density_stable_focal_anchor")
        self.assertEqual(competing["visual_density"]["classification"], "high_density_competing_focal_regions")

    def test_insufficient_evidence_remains_limited(self):
        data = build_intelligence_v3([frame(0)])
        self.assertEqual(data["confidence"]["observation_confidence"], "limited")
        self.assertEqual(data["visual_cadence"]["progression"], "insufficient_evidence")


class EvidenceQualificationV3Tests(unittest.TestCase):
    def test_evidence_object_serialization_and_states(self):
        finding = EvidenceFinding(
            "id", "type", 0, 1, 3, availability_state="conflicting",
            conflicting_observations=[{"value": 2}],
        )
        self.assertEqual(finding.to_dict()["availability_state"], "conflicting")
        self.assertEqual(len(AVAILABILITY_STATES), 5)

    def test_invalid_availability_state_is_rejected(self):
        with self.assertRaises(ValueError):
            EvidenceFinding("id", "type", 0, 1, 3, availability_state="invented")

    def test_confidence_dimensions_are_separate(self):
        data = build_intelligence_v3([frame(index) for index in range(8)])
        self.assertEqual(set(data["confidence"]) - {"reasons"}, {
            "observation_confidence", "interpretation_confidence",
            "recommendation_confidence",
        })
        self.assertEqual(data["confidence"]["observation_confidence"], "high")
        self.assertEqual(data["confidence"]["recommendation_confidence"], "limited")

    def test_benchmark_unavailable_and_qualified(self):
        unavailable = build_intelligence_v3([frame(i) for i in range(3)])
        qualified = build_intelligence_v3(
            [frame(i) for i in range(3)],
            {"benchmark_quality": {"eligible_for_directional_learning": True},
             "qualified": [{}, {}, {}]},
        )
        self.assertEqual(unavailable["benchmark_context"]["availability_state"], "unavailable")
        self.assertEqual(qualified["benchmark_context"]["sample_size"], 3)


class ReasoningAndExperimentV3Tests(unittest.TestCase):
    def test_static_interval_produces_operational_direct_evidence_experiment(self):
        value = report([frame(index) for index in range(5)])
        reasoning = build_creative_reasoning(value)
        experiment = reasoning["experiments"][0]
        for key in (
            "source_finding_ids", "variable", "control", "exact_execution",
            "target_timing", "expected_observable_change", "measurement_plan",
            "evidence_basis", "invalidation_criteria",
        ):
            self.assertTrue(experiment[key])
        self.assertFalse(experiment["benchmark_supported"])

    def test_opportunity_ranking_prefers_qualified_actionable_finding(self):
        reasoning = build_creative_reasoning(report([frame(index) for index in range(5)]))
        self.assertEqual(reasoning["priority"]["structural_dimension"], "visual_change_timing")
        self.assertIn("magnitude_actionability_score", reasoning["priority"]["ranking"])

    def test_duplicate_suppression_keeps_unique_dimensions(self):
        reasoning = build_creative_reasoning(report([frame(index) for index in range(5)]))
        dimensions = [item["structural_dimension"] for item in reasoning["experiments"]]
        self.assertEqual(len(dimensions), len(set(dimensions)))

    def test_required_abstention_when_evidence_is_insufficient(self):
        reasoning = build_creative_reasoning(report([frame(0)]))
        self.assertEqual(reasoning["experiments"], [])

    def test_creator_report_preserves_v3_confidence_and_plain_language(self):
        value = report([frame(index) for index in range(5)])
        creator = build_creator_report(value, build_creative_reasoning(value))
        self.assertIn("confidence_breakdown", creator)
        self.assertNotIn("viewer will", str(creator).lower())
        self.assertNotIn("retention will improve", str(creator).lower())

    def test_creator_timeline_exposes_meaningful_events_without_internal_ids(self):
        value = report([frame(0), frame(2, composition="close"), frame(3, composition="close")])
        creator = build_creator_report(value, build_creative_reasoning(value))
        self.assertIn("2.0s", creator["intro_timeline"][0]["time"])
        self.assertNotIn("v3-", str(creator["intro_timeline"]))


class ObjectiveValidationV3Tests(unittest.TestCase):
    def _codes(self, experiment, benchmark=None):
        value = {"status": "success", "benchmark": benchmark or {},
                 "creator_report": {
                     "opening_snapshot": {}, "creative_understanding": {},
                     "biggest_opportunity": {"supported": True},
                     "experiments": [experiment],
                     "confidence_summary": {"text_evidence": "moderate"},
                     "limitations": ["No outcome evidence."],
                 }}
        return {item["code"] for item in run_quality_checks(value)}

    def test_generic_advice_warning(self):
        codes = self._codes({"title": "Test", "change": "Make it more engaging",
                             "confidence": "limited"})
        self.assertIn("generic_recommendation", codes)

    def test_unsupported_performance_claim_warning(self):
        codes = self._codes({"title": "Test", "change": "Improve retention",
                             "confidence": "moderate"})
        self.assertIn("unsupported_performance_claim", codes)

    def test_missing_operational_fields_are_warned(self):
        codes = self._codes({"title": "Test", "change": "Change crop",
                             "confidence": "moderate"})
        self.assertTrue({
            "missing_target_timing", "missing_measurable_variable",
            "missing_control", "missing_evidence_reference",
            "missing_invalidation_criteria",
        }.issubset(codes))

    def test_typed_non_applicable_timing_does_not_warn(self):
        experiment = {
            "title": "Test", "change": "Change crop", "confidence": "moderate",
            "target_timing": {"applicability": "not_applicable"},
        }
        self.assertNotIn("missing_target_timing", self._codes(experiment))

    def test_false_benchmark_support_is_warned(self):
        experiment = {
            "title": "Test", "change": "Change crop", "confidence": "moderate",
            "benchmark_supported": True,
        }
        self.assertIn("false_benchmark_support", self._codes(experiment))

    def test_complete_v3_experiment_avoids_generic_contract_warnings(self):
        value = report([frame(index) for index in range(5)])
        reasoning = build_creative_reasoning(value)
        creator = build_creator_report(value, reasoning)
        value["creator_report"] = creator
        codes = {item["code"] for item in run_quality_checks(value)}
        self.assertFalse({
            "generic_recommendation", "missing_target_timing",
            "missing_measurable_variable", "missing_control",
            "missing_execution_instruction", "missing_evidence_reference",
            "missing_invalidation_criteria",
        } & codes)


if __name__ == "__main__":
    unittest.main()
