import unittest
from unittest.mock import patch

from core.creator_report import build_creator_report
from core.evaluation.evaluation_metrics import calculate_metrics
from core.evaluation.evaluation_models import EvaluationResult
from core.observers.semantic_observer import observe_semantics
from core.reasoning.creative_reasoning import _rank_candidates, build_creative_reasoning
from core.understanding import understand_creative_opening


def semantic():
    frames = [
        {"timestamp": 0, "scene_type": "text_led", "text_overlay": True, "motion_score": 0},
        {"timestamp": 1, "scene_type": "text_led", "text_overlay": True, "motion_score": 0},
        {"timestamp": 2, "human_presence": True, "scene_type": "person_focused", "text_overlay": True, "motion_score": 8},
        {"timestamp": 3, "human_presence": True, "scene_type": "person_focused", "text_overlay": True, "motion_score": 8},
    ]
    return observe_semantics(frames)


class CreativeReasoningIntegrationTests(unittest.TestCase):
    def test_reasoning_consumes_supplied_understanding_and_structure(self):
        observed = semantic()
        structure, understanding = understand_creative_opening(observed)
        structure_value = {**structure.to_dict(), "opening_strategy": "supplied-strategy"}
        understanding_value = {**understanding.to_dict(), "summary": "Supplied structural understanding."}
        result = build_creative_reasoning({
            "semantic_observation": observed,
            "creative_structure": structure_value,
            "creative_understanding": understanding_value,
        })
        self.assertEqual(result["opening_snapshot"], "Supplied structural understanding.")
        self.assertEqual(result["creative_structure"]["opening_strategy"], "supplied-strategy")
        self.assertFalse(result["traceability"]["compatibility_mode"])

    def test_legacy_compatibility_builds_inputs_once(self):
        result = build_creative_reasoning({"semantic_observation": semantic()})
        self.assertTrue(result["traceability"]["compatibility_mode"])
        self.assertTrue(result["creative_understanding"]["summary"])
        self.assertEqual(
            result["creative_structure"], result["traceability"]["creative_structure"]
        )

    def test_opportunities_are_supported_ranked_and_traceable(self):
        observed = semantic()
        structure, understanding = understand_creative_opening(observed)
        result = build_creative_reasoning({
            "semantic_observation": observed,
            "creative_structure": structure.to_dict(),
            "creative_understanding": understanding.to_dict(),
        })
        self.assertTrue(result["opportunity_candidates"])
        self.assertEqual(result["priority"], result["opportunity_candidates"][0])
        for candidate in result["opportunity_candidates"]:
            self.assertTrue(candidate["supporting_evidence"])
            self.assertIn("score", candidate["ranking"])
            self.assertEqual(candidate["current_structure"], result["creative_structure"][
                "information_order" if candidate["structural_dimension"] == "information_order" else
                "information_density" if candidate["structural_dimension"] == "information_density" else
                "structural_rhythm" if candidate["structural_dimension"] == "structural_rhythm" else
                "visual_anchor" if candidate["structural_dimension"] == "visual_anchor" else "reveal_pattern"
            ])

    def test_ranking_penalizes_contradictory_or_missing_evidence(self):
        base = {
            "structural_dimension": "visual_anchor", "current_structure": "mixed elements",
            "alternative_structure": "single anchor", "evidence_count": 2,
            "structural_importance": "high", "confidence": "moderate",
            "benchmark_supported": False,
        }
        consistent = {**base, "title": "consistent", "evidence_consistency": "consistent"}
        contradictory = {**base, "title": "contradictory", "evidence_consistency": "limited"}
        ranked = _rank_candidates([contradictory, consistent])
        self.assertEqual(ranked[0]["title"], "consistent")
        self.assertGreater(ranked[1]["ranking"]["contradiction_penalty"], 0)

    def test_unknown_limited_and_stable_inputs_do_not_invent_advice(self):
        self.assertEqual(build_creative_reasoning({})["experiments"], [])
        one = observe_semantics([{"timestamp": 0, "human_presence": True}])
        self.assertEqual(build_creative_reasoning({"semantic_observation": one})["experiments"], [])
        stable = observe_semantics([
            {"timestamp": index, "human_presence": True, "scene_type": "person_focused", "motion_score": 0}
            for index in range(4)
        ])
        result = build_creative_reasoning({"semantic_observation": stable})
        self.assertEqual(result["experiments"], [])
        self.assertIsNone(result["priority"])

    def test_experiments_are_deduplicated_by_structural_dimension(self):
        observed = semantic()
        structure, understanding = understand_creative_opening(observed)
        result = build_creative_reasoning({
            "semantic_observation": observed,
            "creative_structure": {
                **structure.to_dict(), "visual_anchor": "mixed elements",
                "attention_evolution": "moves through frequent purpose changes",
                "structural_rhythm": "multi-phase progression",
            },
            "creative_understanding": understanding.to_dict(),
        })
        dimensions = [item["structural_dimension"] for item in result["experiments"]]
        self.assertEqual(len(dimensions), len(set(dimensions)))
        self.assertGreaterEqual(len(dimensions), 2)

    def test_creator_synthesis_and_evaluation_metrics(self):
        observed = semantic()
        structure, understanding = understand_creative_opening(observed)
        report = {
            "semantic_observation": observed, "creative_structure": structure.to_dict(),
            "creative_understanding": understanding.to_dict(), "benchmark": {}, "patterns": {},
        }
        reasoning = build_creative_reasoning(report)
        report["reasoning"] = {"creative_reasoning": reasoning}
        report["creator_report"] = build_creator_report(report, reasoning)
        self.assertEqual(report["creator_report"]["opening_snapshot"]["summary"], understanding.summary)
        self.assertNotIn("text is present", str(report["creator_report"]).lower())
        metrics = calculate_metrics([EvaluationResult("v", "V", "test", "success", 0.1, report)])
        self.assertEqual(metrics["creative_reasoning_trace_rate"]["rate"], 1.0)
        self.assertEqual(metrics["experiment_dimension_diversity_rate"]["rate"], 1.0)

    @patch("ui.advanced.render_evaluation_dashboard")
    @patch("ui.advanced.st")
    def test_builder_traceability_is_hidden_from_creator(self, st, dashboard):
        st.expander.return_value.__enter__.return_value = None
        from ui.advanced import render_advanced_analysis
        report = {"reasoning": {"creative_reasoning": {"traceability": {
            "semantic_evidence": [{"semantic_field": "opening_mode", "observed_value": "subject_first"}],
            "creative_structure": {"opening_strategy": "subject-first"},
            "creative_understanding": {"summary": "A subject-first opening."},
            "opportunity_candidates": [], "selected_opportunity": None, "experiments": [],
        }}}}
        render_advanced_analysis(report, "builder", {})
        captions = [call.args[0] for call in st.caption.call_args_list]
        self.assertIn("Creative reasoning traceability", captions)
        st.caption.reset_mock()
        render_advanced_analysis(report, "creator", {})
        creator_captions = [call.args[0] for call in st.caption.call_args_list]
        self.assertNotIn("Creative reasoning traceability", creator_captions)


if __name__ == "__main__":
    unittest.main()
