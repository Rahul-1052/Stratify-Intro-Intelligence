import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from core.beta.real_world_validation import (
    ANNOTATION_METRICS,
    RealWorldValidationRunner,
    create_case,
    expectation_hash,
    load_manifest,
    lock_expectations,
    mark_analysis_started,
    verify_expectations_lock,
)


class RealWorldValidationV1Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.manifest = self.root / "real_world" / "manifest.json"
        self.manifest.parent.mkdir(parents=True)
        self.manifest.write_text(json.dumps({
            "schema_version": 1,
            "validation_version": "real-world-validation-v1",
            "cases": [],
        }), encoding="utf-8")
        self.clip = self.root / "input.mp4"
        self._write_clip(self.clip)

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def _write_clip(path):
        writer = cv2.VideoWriter(
            str(path), cv2.VideoWriter_fourcc(*"mp4v"), 5.0, (32, 24)
        )
        for index in range(5):
            writer.write(np.full((24, 32, 3), index * 20, dtype=np.uint8))
        writer.release()

    def _create(self, case_id="rw-001"):
        return create_case(
            self.manifest, case_id, "Static intro", "education", self.clip,
            now="2026-01-01T00:00:00+00:00",
        )

    def _set_expectations(self, expectations, case_id="rw-001"):
        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        case = next(item for item in payload["cases"] if item["case_id"] == case_id)
        case["expectations"] = expectations
        self.manifest.write_text(json.dumps(payload), encoding="utf-8")

    @staticmethod
    def _report():
        return {
            "vision": {
                "visual_energy": "moderate",
                "frame_observations": [
                    {
                        "timestamp": 0,
                        "motion_score": 0.2,
                        "human_presence": True,
                        "text_overlay": False,
                    },
                    {
                        "timestamp": 1,
                        "motion_score": 0.4,
                        "human_presence": True,
                        "text_overlay": True,
                        "text_overlay_confidence": "high",
                    },
                ],
            },
            "intelligence_v3": {
                "confidence": {
                    "observation_confidence": "high",
                    "interpretation_confidence": "moderate",
                },
                "meaningful_change_events": [
                    {"event_type": "scene_change", "timestamp": 1}
                ],
                "visual_change_timing": {"scene_continuity": 0.8},
                "visual_novelty": {"average": 0.3},
                "visual_density": {
                    "classification": "moderate",
                    "focal_stability": "high",
                    "average_visible_elements": 3,
                },
            },
        }

    def test_manifest_loading_and_required_schema(self):
        self._create()
        loaded = load_manifest(self.manifest)
        self.assertEqual(loaded["cases"][0]["case_id"], "rw-001")
        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        del payload["cases"][0]["annotator"]
        self.manifest.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "annotator"):
            load_manifest(self.manifest)

    def test_case_creation_copies_validated_clip(self):
        case = self._create()
        copied = self.manifest.parent / case["clip_path"]
        self.assertTrue(copied.is_file())
        self.assertGreater(case["duration_seconds"], 0)
        self.assertEqual(case["annotation_status"], "not_started")

    def test_case_creation_can_reference_clip(self):
        case = create_case(
            self.manifest, "rw-ref", "Reference", "podcast", self.clip,
            copy_clip=False,
        )
        self.assertEqual(Path(case["clip_path"]), self.clip.resolve())

    def test_expectation_locking_records_hash_and_timestamp(self):
        self._create()
        expectations = [{
            "metric": "scene_change_count", "expected_value": [0, 2],
            "comparison": "numeric_range",
        }]
        self._set_expectations(expectations)
        case = lock_expectations(
            self.manifest, "rw-001", "Tester",
            now="2026-01-02T00:00:00+00:00",
        )
        self.assertEqual(case["expectations_hash"], expectation_hash(expectations))
        self.assertEqual(case["annotation_status"], "locked")
        self.assertTrue(verify_expectations_lock(case))

    def test_hash_mismatch_is_detected_after_analysis_begins(self):
        self._create()
        self._set_expectations([{
            "metric": "scene_change_count", "expected_value": 1,
            "comparison": "exact",
        }])
        lock_expectations(self.manifest, "rw-001")
        mark_analysis_started(self.manifest, ["rw-001"])
        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        payload["cases"][0]["expectations"][0]["expected_value"] = 2
        self.manifest.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed"):
            mark_analysis_started(self.manifest, ["rw-001"])

    def test_unlocked_case_cannot_start_analysis(self):
        self._create()
        with self.assertRaisesRegex(ValueError, "not locked"):
            mark_analysis_started(self.manifest, ["rw-001"])

    def test_run_outputs_normalization_partial_coverage_and_no_leakage(self):
        self._create()
        self._set_expectations([
            {
                "metric": "scene_change_count", "expected_value": 1,
                "comparison": "exact",
            },
            {
                "metric": "text_intro_seconds", "expected_value": 2,
                "comparison": "temporal_before",
            },
        ])
        lock_expectations(self.manifest, "rw-001", "Tester")
        calls = []

        def analyzer(clip_path, no_network):
            calls.append((clip_path, no_network))
            return self._report()

        run, location = RealWorldValidationRunner(analyzer).run(
            self.manifest, output_dir=self.root / "runs", run_id="test-run"
        )
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][1])
        self.assertEqual(len(calls[0]), 2)
        self.assertFalse(run["observation_pipeline_received_expectations"])
        self.assertGreaterEqual(run["cases"][0]["normalized_metric_count"], 14)
        self.assertEqual(
            run["coverage"]["manual_annotation_coverage"],
            round(2 / len(ANNOTATION_METRICS), 4),
        )
        required = [
            "run.json", "cases/rw-001.json", "accuracy/summary.json",
            "accuracy/summary.md", "accuracy/cases/rw-001.json",
            "accuracy/cases/rw-001.md",
        ]
        self.assertTrue(all((location / item).is_file() for item in required))

    def test_unavailable_metrics_are_reported(self):
        self._create()
        self._set_expectations([{
            "metric": "information_intro_seconds", "expected_value": 2,
            "comparison": "temporal_before", "required": True,
        }])
        lock_expectations(self.manifest, "rw-001")
        _, location = RealWorldValidationRunner(
            lambda clip_path, no_network: {"vision": {}, "intelligence_v3": {}}
        ).run(self.manifest, output_dir=self.root / "runs", run_id="unavailable")
        result = json.loads(
            (location / "accuracy/cases/rw-001.json").read_text(encoding="utf-8")
        )
        self.assertEqual(result["unavailable_metrics"], 1)
        self.assertEqual(result["evaluability_coverage"], 0.0)

    def test_empty_locked_expectations_report_zero_coverage(self):
        self._create()
        lock_expectations(self.manifest, "rw-001")
        run, location = RealWorldValidationRunner(
            lambda clip_path, no_network: self._report()
        ).run(self.manifest, output_dir=self.root / "runs", run_id="empty")
        self.assertEqual(run["coverage"]["manual_annotation_coverage"], 0.0)
        summary = json.loads(
            (location / "accuracy/summary.json").read_text(encoding="utf-8")
        )
        self.assertEqual(summary["unevaluable_cases"], 1)

    def test_real_world_module_does_not_depend_on_golden_runner(self):
        module = (
            Path(__file__).parents[1] / "core/beta/real_world_validation.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("core.beta.golden", module)
        self.assertNotIn("core.beta.synthetic_clips", module)
        golden = Path(__file__).parents[1] / "validation/golden_dataset/manifest.json"
        before = hashlib.sha256(golden.read_bytes()).hexdigest()
        load_manifest(self.manifest)
        after = hashlib.sha256(golden.read_bytes()).hexdigest()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
