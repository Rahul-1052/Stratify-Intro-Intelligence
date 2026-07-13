import json
import unittest
from unittest.mock import patch

from core.viewer_job_comparison import compare_viewer_jobs


IDENTITY = {
    "subject": "a recorded activity",
    "viewer_intent": "watch the activity unfold for entertainment",
    "presentation_style": "events are shown directly",
    "storytelling_format": "a challenge develops toward an outcome",
    "source_context": "the uploader presents the recorded activity",
}


def _response(payload):
    return {"status": "success", "content": json.dumps(payload), "provider": "test"}


class ViewerJobComparisonTests(unittest.TestCase):
    @patch("core.providers.provider_router.observe_text")
    def test_minor_source_and_presentation_differences_do_not_reject_core_match(self, observe):
        observe.return_value = _response({
            "reference_to_candidate": {"viewer_intent_score": 0.88, "storytelling_job_score": 0.86},
            "candidate_to_reference": {"viewer_intent_score": 0.87, "storytelling_job_score": 0.85},
            "presentation_compatibility": 0.42,
            "source_context_compatibility": 0.30,
            "same_viewing_job": True,
            "confidence": "high",
            "reason": "Different creator and presentation polish.",
        })

        result = compare_viewer_jobs(IDENTITY, IDENTITY)

        self.assertTrue(result["same_viewing_job"])
        self.assertIn(result["confidence"], {"high", "strong"})
        self.assertIn("compatible", result["reason"].lower())

    @patch("core.providers.provider_router.observe_text")
    def test_shared_subject_cannot_override_different_core_job(self, observe):
        observe.return_value = _response({
            "reference_to_candidate": {"viewer_intent_score": 0.38, "storytelling_job_score": 0.31},
            "candidate_to_reference": {"viewer_intent_score": 0.40, "storytelling_job_score": 0.33},
            "presentation_compatibility": 0.90,
            "source_context_compatibility": 0.90,
            "same_viewing_job": False,
            "confidence": "high",
            "reason": "One presents the activity; the other critiques it.",
        })

        result = compare_viewer_jobs(IDENTITY, IDENTITY)

        self.assertFalse(result["same_viewing_job"])
        self.assertEqual(result["confidence"], "low")

    @patch("core.providers.provider_router.observe_text")
    def test_material_asymmetry_gets_one_bounded_adjudication(self, observe):
        observe.side_effect = [
            _response({
                "reference_to_candidate": {"viewer_intent_score": 0.90, "storytelling_job_score": 0.88},
                "candidate_to_reference": {"viewer_intent_score": 0.58, "storytelling_job_score": 0.56},
                "presentation_compatibility": 0.70,
                "source_context_compatibility": 0.60,
                "same_viewing_job": False,
                "confidence": "low",
                "reason": "Directional result is uncertain.",
            }),
            _response({
                "reference_to_candidate": {"viewer_intent_score": 0.82, "storytelling_job_score": 0.80},
                "candidate_to_reference": {"viewer_intent_score": 0.80, "storytelling_job_score": 0.79},
                "presentation_compatibility": 0.65,
                "source_context_compatibility": 0.55,
                "same_viewing_job": True,
                "confidence": "high",
                "reason": "The core jobs are substitutes.",
            }),
        ]

        result = compare_viewer_jobs(IDENTITY, IDENTITY)

        self.assertEqual(observe.call_count, 2)
        self.assertTrue(result["second_pass_used"])
        self.assertTrue(result["same_viewing_job"])

    @patch("core.providers.provider_router.observe_text")
    def test_consistent_borderline_substitute_is_not_rejected(self, observe):
        payload = {
            "reference_to_candidate": {
                "viewer_intent_score": 0.72,
                "storytelling_job_score": 0.72,
            },
            "candidate_to_reference": {
                "viewer_intent_score": 0.72,
                "storytelling_job_score": 0.72,
            },
            "presentation_compatibility": 0.45,
            "source_context_compatibility": 0.35,
            "same_viewing_job": True,
            "confidence": "moderate",
            "reason": "The core jobs remain substitutes despite source differences.",
        }
        observe.return_value = _response(payload)

        result = compare_viewer_jobs(IDENTITY, IDENTITY)

        self.assertTrue(result["same_viewing_job"])
        self.assertEqual(result["core_compatibility"], 0.72)
        self.assertIn("compatible", result["reason"].lower())
        self.assertLessEqual(observe.call_count, 2)


if __name__ == "__main__":
    unittest.main()
