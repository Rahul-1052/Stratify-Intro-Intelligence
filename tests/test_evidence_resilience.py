import math
import unittest

from core.benchmark_signature import build_benchmark_signature, compare_benchmark_signatures
from core.pattern_discovery import discover_patterns
from core.reasoning.pattern_learning_engine import learn_benchmark_patterns


class EvidenceResilienceTests(unittest.TestCase):
    def test_signature_survives_structured_provider_values(self):
        reference = build_benchmark_signature(
            video={"title": "A creator tests an idea", "duration": "PT2M"},
            vision={"scene_type": {"primary": "studio"}, "frame_observations": [{"text_overlay": ["present"]}]},
        )
        candidate = build_benchmark_signature(
            video={"title": "Testing a creator idea", "duration": 125},
            vision={"scene_type": {"primary": "studio"}},
        )
        result = compare_benchmark_signatures(reference, candidate)
        self.assertIn("compatibility_score", result)
        self.assertGreater(reference["availability"]["evidence_count"], 1)

    def test_pattern_discovery_handles_structured_and_nonfinite_values(self):
        top = [{"feature_summary": {"layout": {"subject": "center"}, "pace": 2}}] * 2
        lower = [{"feature_summary": {"layout": {"subject": "edge"}, "pace": 1}}] * 2
        user = {"feature_summary": {"layout": {"subject": "edge"}, "pace": math.nan}}
        result = discover_patterns(top, lower, user)
        self.assertEqual(result["discovered_feature_count"], 2)
        self.assertTrue(any(item["feature"] == "layout" for item in result["recommendations"]))
        self.assertFalse(any(item["feature"] == "pace" for item in result["recommendations"]))

    def test_secondary_learning_rejects_unknown_evidence(self):
        evidence = {
            "top_performers": [
                {"features": {"feature_summary": {"lighting": "unknown", "motion": "high"}}},
                {"features": {"feature_summary": {"lighting": None, "motion": "high"}}},
            ],
            "lower_performers": [
                {"features": {"feature_summary": {"lighting": "dim", "motion": "low"}}},
                {"features": {"feature_summary": {"lighting": "dim", "motion": "low"}}},
            ],
        }
        result = learn_benchmark_patterns(evidence)
        self.assertNotIn("lighting", result["top_patterns"])
        motion = next(item for item in result["discriminative_patterns"] if item["feature"] == "motion")
        self.assertEqual(motion["frequency_gap"], 1.0)


if __name__ == "__main__":
    unittest.main()
