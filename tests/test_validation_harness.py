import json
import unittest
from pathlib import Path

from scripts.validate_benchmark_pipeline import (
    _calculate_metrics,
    _compact_report,
    _resolve_source,
)


class ValidationHarnessTests(unittest.TestCase):
    def test_saved_real_source_is_used_when_live_search_fails(self):
        def failed_search(**_kwargs):
            raise RuntimeError("provider quota exhausted")

        previous = {
            "source_video": {
                "video_id": "saved-video-id",
                "title": "Previously resolved real video",
            }
        }

        matches, resolution = _resolve_source(failed_search, "query", previous)

        self.assertEqual(matches[0]["video_id"], "saved-video-id")
        self.assertEqual(resolution["mode"], "saved_real_source_fallback")
        self.assertIn("quota exhausted", resolution["warning"])

    def test_source_fallback_warning_is_preserved_in_compact_report(self):
        report = {"warnings": [], "benchmark": {}, "patterns": {}}
        result = _compact_report(
            {"index": 0},
            {"video_id": "saved-video-id"},
            report,
            source_resolution={
                "mode": "saved_real_source_fallback",
                "warning": "Live source search failed: quota exhausted",
            },
        )

        self.assertEqual(len(result["warnings"]), 1)
        self.assertIn("quota exhausted", result["warnings"][0])

    def test_metrics_capture_calibration_and_runtime_evidence(self):
        metrics = _calculate_metrics([
            {
                "report_status": "success",
                "qualification_status": "success",
                "recommendations": [{"title": "test"}],
                "processing_seconds": 12.5,
                "qualification_diagnostics": [
                    {
                        "qualification_status": "selected",
                        "evidence_mode": "fully_observed",
                        "evidence_coverage": 0.8,
                    }
                ],
                "observed_candidates": [{"status": "success"}],
            },
            {
                "report_status": "partial",
                "qualification_status": "limited",
                "recommendations": [],
                "processing_seconds": 7.5,
                "qualification_diagnostics": [
                    {
                        "qualification_status": "rejected",
                        "rejection_reason": "Different core job.",
                        "evidence_mode": "fully_observed",
                        "evidence_coverage": 1.0,
                    }
                ],
                "observed_candidates": [{"status": "failed"}],
            },
        ])

        self.assertEqual(metrics["coherent_neighborhood_count"], 1)
        self.assertEqual(metrics["qualification_rate"], 0.5)
        self.assertEqual(metrics["abstention_rate"], 0.5)
        self.assertEqual(metrics["recommendation_rate"], 0.5)
        self.assertEqual(metrics["acquisition_failures"], 1)
        self.assertEqual(metrics["total_processing_seconds"], 20.0)

    def test_real_validation_artifact_integrity(self):
        artifact_path = (
            Path(__file__).resolve().parents[1]
            / "validation"
            / "benchmark_qualification"
            / "real_validation_results.json"
        )
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        results = payload["results"]

        self.assertEqual(len(results), 12)
        indices = [item["case"]["index"] for item in results]
        self.assertEqual(indices, list(range(12)))
        self.assertEqual(len(set(indices)), 12)

        required = {
            "metadata_compatibility",
            "observed_intro_compatibility",
            "evidence_coverage",
            "qualification_status",
            "rejection_reason",
            "evidence_mode",
        }
        for result in results:
            if result.get("qualification_status") == "limited":
                self.assertFalse(result.get("recommendations"))
            observed_status = {
                item.get("video", {}).get("video_id"): item.get("status")
                for item in result.get("observed_candidates", [])
            }
            for diagnostic in result.get("qualification_diagnostics", []):
                self.assertTrue(required.issubset(diagnostic))
                if diagnostic.get("qualification_status") == "selected":
                    self.assertEqual(diagnostic.get("evidence_mode"), "fully_observed")
                    self.assertEqual(observed_status.get(diagnostic.get("video_id")), "success")


if __name__ == "__main__":
    unittest.main()
