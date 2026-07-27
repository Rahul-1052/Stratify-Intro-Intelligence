import unittest
from unittest.mock import patch

from ui.creator_report_v4 import (
    _benchmark_available,
    _confidence_value,
    _direct_evidence_available,
    _verdict,
    story_events,
    strongest_finding,
    render_creator_report_v4,
)


def finding(identifier="change", qualified=True):
    return {
        "finding_id": identifier,
        "observation_type": "meaningful_visual_change",
        "start_time": 0, "end_time": 5,
        "measured_value": {"change_count": 2},
        "evidence_strength": "moderate",
        "availability_state": (
            "available_and_qualified" if qualified else "available_but_weak"
        ),
        "qualification_result": "qualified" if qualified else "not_qualified",
        "supporting_observations": [], "conflicting_observations": [],
        "limitations": ["Sampled evidence."],
    }


def creator(supported=True):
    return {
        "opening_snapshot": {"summary": "The opening holds one visible state."},
        "biggest_opportunity": {
            "title": "Test an earlier visual update",
            "summary": "The opening holds one state through the early window.",
            "why_test": "The first measured change occurs later.",
            "limitation": "No outcome evidence.",
            "supported": supported,
        },
        "experiments": ([{
            "title": "Move one update earlier",
            "source_finding_ids": ["change"],
            "variable": "visual change timing",
        }] if supported else []),
        "confidence_breakdown": {
            "observation_confidence": "high",
            "interpretation_confidence": "moderate",
            "recommendation_confidence": "moderate" if supported else "limited",
        },
        "evidence_validation": {"benchmark_supported": False},
        "limitations": [],
    }


def report():
    return {
        "status": "success",
        "vision": {"frame_observations": [{"timestamp": 0}, {"timestamp": 5}]},
        "intelligence_v3": {
            "meaningful_change_events": [{
                "timestamp": 5, "event_type": "scene_change",
                "previous_state": "room", "new_state": "street",
                "evidence_strength": "moderate",
            }],
            "visual_change_timing": {
                "longest_stable_interval": {
                    "start_time": 0, "end_time": 5, "duration": 5,
                },
            },
            "findings": [finding()],
        },
        "benchmark": {}, "patterns": {},
    }


class CreatorReportV4ModelTests(unittest.TestCase):
    def test_hero_verdict_uses_existing_opportunity(self):
        self.assertEqual(
            _verdict(creator()),
            "The opening holds one state through the early window.",
        )

    def test_abstention_verdict_uses_existing_snapshot(self):
        value = creator(False)
        value["biggest_opportunity"]["summary"] = ""
        self.assertEqual(_verdict(value), "The opening holds one visible state.")

    def test_confidence_dimensions_remain_separate(self):
        value = creator()
        self.assertEqual(_confidence_value(value, "observation_confidence"), "high")
        self.assertEqual(_confidence_value(value, "interpretation_confidence"), "moderate")

    def test_direct_evidence_and_benchmark_availability(self):
        value = report()
        self.assertTrue(_direct_evidence_available(value))
        self.assertFalse(_benchmark_available(value, creator()))
        value["benchmark"] = {
            "benchmark_quality": {"eligible_for_directional_learning": True}
        }
        self.assertTrue(_benchmark_available(value, creator()))

    def test_story_is_chronological_and_contains_first_change_and_stability(self):
        events = story_events(report())
        self.assertEqual([item["timestamp"] for item in events], sorted(
            item["timestamp"] for item in events
        ))
        self.assertIn("First Visual Change", [item["title"] for item in events])
        self.assertIn("Stable Segment", [item["title"] for item in events])

    def test_story_does_not_fabricate_events(self):
        value = report()
        value["intelligence_v3"] = {}
        self.assertEqual(story_events(value), [])

    def test_story_condenses_dense_raw_events(self):
        value = report()
        value["intelligence_v3"]["meaningful_change_events"] = [
            {
                "timestamp": index, "event_type": "composition_change",
                "previous_state": "a", "new_state": "b",
                "evidence_strength": "moderate",
            }
            for index in range(15)
        ]
        self.assertLessEqual(len(story_events(value)), 9)

    def test_strongest_finding_follows_primary_experiment_source(self):
        value = report()
        value["intelligence_v3"]["findings"] = [
            finding("other"), finding("change"),
        ]
        self.assertEqual(
            strongest_finding(value, creator())["finding_id"], "change"
        )


class CreatorReportV4FlowTests(unittest.TestCase):
    @patch("ui.creator_report_v4.render_builder")
    @patch("ui.creator_report_v4.render_trust_limitations")
    @patch("ui.creator_report_v4.render_supporting_evidence")
    @patch("ui.creator_report_v4.render_benchmarks")
    @patch("ui.creator_report_v4.render_confidence")
    @patch("ui.creator_report_v4.render_primary_experiment")
    @patch("ui.creator_report_v4.render_strongest_finding")
    @patch("ui.creator_report_v4.render_story")
    @patch("ui.creator_report_v4.render_hero")
    def test_creator_flow_order_and_builder_isolation(
        self, hero, story, strongest, experiment, confidence, benchmarks,
        evidence, limitations, builder,
    ):
        render_creator_report_v4(report(), creator(), {}, "creator", {})
        for component in (
            hero, story, strongest, experiment, confidence, benchmarks,
            evidence, limitations,
        ):
            component.assert_called_once()
        builder.assert_not_called()

    @patch("ui.creator_report_v4.render_builder")
    @patch("ui.creator_report_v4.render_trust_limitations")
    @patch("ui.creator_report_v4.render_supporting_evidence")
    @patch("ui.creator_report_v4.render_benchmarks")
    @patch("ui.creator_report_v4.render_confidence")
    @patch("ui.creator_report_v4.render_primary_experiment")
    @patch("ui.creator_report_v4.render_strongest_finding")
    @patch("ui.creator_report_v4.render_story")
    @patch("ui.creator_report_v4.render_hero")
    def test_builder_diagnostics_render_only_in_builder(
        self, hero, story, strongest, experiment, confidence, benchmarks,
        evidence, limitations, builder,
    ):
        render_creator_report_v4(report(), creator(), {}, "builder", {})
        builder.assert_called_once()

    @patch("ui.creator_report_v4.render_builder")
    @patch("ui.creator_report_v4.render_trust_limitations")
    @patch("ui.creator_report_v4.render_supporting_evidence")
    @patch("ui.creator_report_v4.render_benchmarks")
    @patch("ui.creator_report_v4.render_confidence")
    @patch("ui.creator_report_v4.render_primary_experiment")
    @patch("ui.creator_report_v4.render_strongest_finding")
    @patch("ui.creator_report_v4.render_story")
    @patch("ui.creator_report_v4.render_hero")
    def test_after_opportunity_hook_remains_supported(
        self, hero, story, strongest, experiment, confidence, benchmarks,
        evidence, limitations, builder,
    ):
        called = []
        render_creator_report_v4(
            report(), creator(), {}, "creator", {},
            after_opportunity=lambda: called.append(True),
        )
        self.assertEqual(called, [True])


if __name__ == "__main__":
    unittest.main()
