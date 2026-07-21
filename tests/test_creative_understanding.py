import unittest
from unittest.mock import patch

from core.evaluation.evaluation_models import EvaluationResult
from core.understanding import CreativeStructure, CreativeUnderstanding, build_creative_structure, understand_creative_opening


def semantic_observation(confidence="moderate"):
    return {
        "opening_mode": "environment_first", "primary_visual_focus": "person",
        "focus_clarity": "develops_early", "visual_progression": "distinct_beats",
        "information_mode": "image_and_text", "text_role": "intermittent",
        "semantic_confidence": confidence,
        "beats": [
            {"beat_purpose": "environment_setup", "transition_type": "opening"},
            {"beat_purpose": "subject_establishment", "transition_type": "semantic_purpose_change"},
            {"beat_purpose": "text_led_context", "transition_type": "semantic_purpose_change"},
        ],
    }


class CreativeUnderstandingTests(unittest.TestCase):
    def test_structure_generation_ignores_nonsemantic_context(self):
        first = build_creative_structure(semantic_observation())
        extra_context = {**semantic_observation(), "title": "Ignore this", "category": "gaming"}
        self.assertEqual(first, build_creative_structure(extra_context))
        self.assertEqual(first.opening_strategy, "context-first")
        self.assertEqual(first.structural_rhythm, "multi-phase progression")
        self.assertEqual(first.reveal_pattern, "anchor develops early")

    def test_understanding_is_non_recommendation(self):
        structure, understanding = understand_creative_opening(semantic_observation())
        self.assertEqual(understanding.primary_strategy, structure.opening_strategy)
        self.assertIn("context-first", understanding.summary)
        self.assertNotIn("should", understanding.summary.lower())
        self.assertNotIn("test", understanding.summary.lower())
        self.assertEqual(understanding.evidence_strength, "moderate")

    def test_empty_unknown_and_limited_evidence_abstain(self):
        structure, understanding = understand_creative_opening({})
        self.assertEqual(structure.opening_strategy, "unavailable")
        self.assertEqual(understanding.evidence_strength, "limited")
        self.assertEqual(understanding.supporting_evidence, [])
        unknown = build_creative_structure({"opening_mode": "invented", "semantic_confidence": "certain"})
        self.assertEqual(unknown.opening_strategy, "unavailable")
        self.assertEqual(unknown.confidence, "limited")

    def test_serialization_round_trip(self):
        structure, understanding = understand_creative_opening(semantic_observation("high"))
        self.assertEqual(CreativeStructure.from_dict(structure.to_dict()), structure)
        self.assertEqual(CreativeUnderstanding.from_dict(understanding.to_dict()), understanding)

    def test_evaluation_result_stores_new_layers_compatibly(self):
        legacy = EvaluationResult("v", "Video", "test", "success", 0.1, {})
        self.assertEqual(legacy.creative_structure, {})
        self.assertIn("creative_understanding", legacy.to_dict())

    @patch("ui.advanced.render_evaluation_dashboard")
    @patch("ui.advanced.st")
    def test_builder_diagnostics_render_both_layers(self, st, dashboard):
        st.expander.return_value.__enter__.return_value = None
        from ui.advanced import render_advanced_analysis
        structure, understanding = understand_creative_opening(semantic_observation())
        render_advanced_analysis({
            "semantic_observation": semantic_observation(),
            "creative_structure": structure.to_dict(),
            "creative_understanding": understanding.to_dict(),
        }, "builder", {})
        subheaders = [call.args[0] for call in st.subheader.call_args_list]
        self.assertIn("Creative Structure", subheaders)
        self.assertIn("Creative Understanding", subheaders)
        dashboard.assert_called_once()

        st.subheader.reset_mock()
        dashboard.reset_mock()
        render_advanced_analysis({
            "creative_structure": structure.to_dict(),
            "creative_understanding": understanding.to_dict(),
        }, "creator", {})
        creator_subheaders = [call.args[0] for call in st.subheader.call_args_list]
        self.assertNotIn("Creative Structure", creator_subheaders)
        self.assertNotIn("Creative Understanding", creator_subheaders)
        dashboard.assert_not_called()


if __name__ == "__main__":
    unittest.main()
