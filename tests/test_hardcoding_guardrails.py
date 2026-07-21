import unittest
from pathlib import Path

from core.creator_report import build_creator_report
from core.observers.semantic_observer import BeatCalibrationConfig, observe_semantics
from core.reasoning.creative_reasoning import build_creative_reasoning
from tools.audit_hardcoding import scan_repository


ROOT = Path(__file__).resolve().parents[1]


def frames():
    return [
        {"timestamp": 0, "human_presence": True, "scene_type": "person_focused", "text_overlay": False, "motion_score": 0},
        {"timestamp": 1, "human_presence": True, "scene_type": "person_focused", "text_overlay": True, "motion_score": 8},
        {"timestamp": 2, "human_presence": True, "scene_type": "person_focused", "text_overlay": True, "motion_score": 8},
    ]


class HardcodingGuardrailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scan = scan_repository(ROOT)

    def test_production_has_no_test_titles_fixed_urls_creators_or_test_imports(self):
        prohibited = {"known_test_video", "fixed_youtube_url", "named_creator_special_case", "production_imports_tests"}
        findings = [item for item in self.scan["findings"] if item["rule"] in prohibited]
        self.assertEqual(findings, [])

    def test_named_media_rules_are_confined_to_documented_dormant_legacy_modules(self):
        active = {
            "core/stratify_report.py", "core/creator_report.py",
            "core/reasoning/creative_reasoning.py", "core/category_intelligence.py",
            "core/content_understanding.py", "core/benchmark_intelligence_v2.py",
        }
        findings = [item for item in self.scan["findings"] if item["rule"] == "named_media_or_category_rule" and item["file"].replace("\\", "/") in active]
        self.assertEqual(findings, [])

    def test_full_title_never_changes_direct_creator_reasoning(self):
        semantic = observe_semantics(frames())
        first = build_creator_report({"video": {"title": "Named Movie Character"}, "semantic_observation": semantic, "benchmark": {}, "patterns": {}})
        second = build_creator_report({"video": {"title": "Unrelated Tutorial Creator"}, "semantic_observation": semantic, "benchmark": {}, "patterns": {}})
        self.assertEqual(first, second)
        self.assertNotIn("Named Movie Character", str(first))

    def test_one_primitive_frame_cannot_trigger_an_experiment(self):
        semantic = observe_semantics([frames()[1]])
        reasoning = build_creative_reasoning({"semantic_observation": semantic})
        self.assertEqual(reasoning["experiments"], [])

    def test_benchmark_support_requires_quality_gate(self):
        semantic = observe_semantics(frames())
        base = {"semantic_observation": semantic, "patterns": {"top_creator_experiments": [{"title": "Fixed test", "suggested_test": "Change it", "why_it_matters": "Claim"}]}}
        unsupported = build_creator_report({**base, "benchmark": {"benchmark_quality": {"eligible_for_directional_learning": False}}})
        supported = build_creator_report({**base, "benchmark": {"benchmark_quality": {"eligible_for_directional_learning": True}}})
        self.assertFalse(any(item["benchmark_supported"] for item in unsupported["experiments"]))
        self.assertTrue(any(item["benchmark_supported"] for item in supported["experiments"]))

    def test_missing_evidence_has_no_fixed_recommendations(self):
        reasoning = build_creative_reasoning({})
        self.assertEqual(reasoning["experiments"], [])
        self.assertEqual(reasoning["insights"], [])

    def test_important_semantic_thresholds_are_centralized_and_documented(self):
        fields = BeatCalibrationConfig.__dataclass_fields__
        self.assertTrue({"minimum_persistent_samples", "brief_interruption_samples", "alternating_min_states", "frequent_change_ratio", "frequent_change_min_beats"}.issubset(fields))
        self.assertIn("persistence", BeatCalibrationConfig.__doc__.lower())


if __name__ == "__main__":
    unittest.main()
