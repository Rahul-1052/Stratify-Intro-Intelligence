import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from core.beta.synthetic_clips import (
    CASE_IDS,
    clip_filename,
    generate_clip,
    generate_golden_clips,
    render_frame,
    update_manifest,
    validate_video,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "validation" / "golden_dataset" / "manifest.json"


class GoldenClipGeneratorTests(unittest.TestCase):
    def _manifest_copy(self, folder):
        path = Path(folder) / "manifest.json"
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for case in payload["cases"][:10]:
            case["local_clip_path"] = ""
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_correct_first_ten_case_ids(self):
        self.assertEqual(
            CASE_IDS,
            tuple(f"gd-{index:03d}-{suffix}" for index, suffix in (
                (1, "static-talking-head"), (2, "rapid-montage"),
                (3, "early-subject"), (4, "delayed-subject"),
                (5, "early-text"), (6, "late-text"),
                (7, "frequent-scenes"), (8, "no-scenes"),
                (9, "stable-anchor"), (10, "competing-focal"),
            )),
        )

    def test_case_mapping_is_deterministic(self):
        first = render_frame(CASE_IDS[1], 17)
        second = render_frame(CASE_IDS[1], 17)
        self.assertTrue(np.array_equal(first, second))
        self.assertFalse(np.array_equal(first, render_frame(CASE_IDS[1], 18)))

    def test_clip_filename_rejects_unknown_case(self):
        self.assertEqual(clip_filename(CASE_IDS[0]), f"{CASE_IDS[0]}.mp4")
        with self.assertRaises(ValueError):
            clip_filename("unknown")

    def test_manifest_path_update_preserves_unrelated_cases(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self._manifest_copy(folder)
            before = json.loads(path.read_text(encoding="utf-8"))
            updated = update_manifest(path, {
                CASE_IDS[0]: f"clips/{CASE_IDS[0]}.mp4",
            })
            after = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(updated, 1)
        self.assertEqual(
            after["cases"][0]["local_clip_path"],
            f"clips/{CASE_IDS[0]}.mp4",
        )
        self.assertEqual(before["cases"][10:], after["cases"][10:])
        self.assertEqual(
            {key: value for key, value in before["cases"][0].items()
             if key != "local_clip_path"},
            {key: value for key, value in after["cases"][0].items()
             if key != "local_clip_path"},
        )

    def test_generate_orchestration_creates_clip_directory_and_updates_ten(self):
        calls = []
        def fake_generator(case_id, destination, force=False):
            calls.append((case_id, Path(destination), force))
            Path(destination).write_bytes(b"synthetic")
            return {"status": "generated", "valid": True}
        with tempfile.TemporaryDirectory() as folder:
            manifest = self._manifest_copy(folder)
            clips = Path(folder) / "nested" / "clips"
            result = generate_golden_clips(
                manifest, clips_dir=clips, generator=fake_generator
            )
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            paths = {
                item["case_id"]: item["local_clip_path"]
                for item in payload["cases"][:10]
            }
        self.assertEqual([item[0] for item in calls], list(CASE_IDS))
        self.assertEqual(result["manifest_updated"], 10)
        self.assertTrue(all(value.startswith("nested/clips/") for value in paths.values()))

    def test_lightweight_video_generation_and_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tiny.mp4"
            result = generate_clip(
                CASE_IDS[0], path, fps=5, duration=0.6, size=(160, 90)
            )
            validation = validate_video(path)
        self.assertEqual(result["status"], "generated")
        self.assertTrue(validation["valid"])
        self.assertGreater(validation["frame_count"], 0)

    def test_generator_skips_valid_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tiny.mp4"
            generate_clip(CASE_IDS[0], path, fps=5, duration=0.6, size=(160, 90))
            second = generate_clip(
                CASE_IDS[0], path, fps=5, duration=0.6, size=(160, 90)
            )
        self.assertEqual(second["status"], "skipped")

    def test_force_regeneration_recreates_valid_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tiny.mp4"
            generate_clip(CASE_IDS[0], path, fps=5, duration=0.6, size=(160, 90))
            forced = generate_clip(
                CASE_IDS[0], path, force=True, fps=5, duration=0.6,
                size=(160, 90),
            )
        self.assertEqual(forced["status"], "generated")
        self.assertTrue(forced["valid"])


if __name__ == "__main__":
    unittest.main()
