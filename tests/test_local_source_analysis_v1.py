import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.memory.schema import SCHEMA_VERSION
from core.source_context import SourceContext, resolve_source_context
from core.stratify_report import run_stratify_report
from ui.report import render_report


def successful_local_intro(path):
    return {
        "status": "success", "frames": [], "vision": {"frame_observations": []},
        "features": {}, "acquisition": {"source": "uploaded_video", "method": "uploaded_video_local_clip", "attempts": []},
        "semantic_observation": {}, "creative_structure": {}, "creative_understanding": {},
        "understanding": {}, "warnings": [], "clip_path": str(path),
    }


class SourceContextTests(unittest.TestCase):
    def test_serialization_and_type_validation(self):
        value = SourceContext("cached_local_clip", local_path="clip.mp4", provenance="cache").validate()
        self.assertEqual(json.loads(json.dumps(value.to_dict()))["source_type"], "cached_local_clip")
        with self.assertRaises(ValueError):
            SourceContext("unsupported", local_path="x").validate()

    def test_local_resolution_is_truthful_and_never_needs_youtube(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "opaque-cache-name.mp4"
            path.write_bytes(b"local")
            with patch("core.youtube_client.extract_video_id") as youtube:
                source = resolve_source_context(local_path=str(path), local_source_type="cached_local_clip")
            youtube.assert_not_called()
            self.assertEqual(source.source_url, "")
            self.assertEqual(source.video_id, "")
            self.assertEqual(source.title, "")
            self.assertEqual(source.creator_or_channel, "")
            self.assertEqual(source.metadata_status, "unavailable")

    def test_youtube_requires_url(self):
        with self.assertRaises(ValueError):
            SourceContext("youtube_url").validate()


class LocalReportTests(unittest.TestCase):
    def _run_local(self, source_type="uploaded_file"):
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "clip.mp4"
        path.write_bytes(b"clip")
        patches = [
            patch("core.stratify_report.get_full_youtube_context"),
            patch("core.stratify_report.analyze_intro_pipeline", return_value=successful_local_intro(path)),
            patch("core.stratify_report.understand_content", return_value={}),
            patch("core.stratify_report.collect_benchmark_videos"),
            patch("core.stratify_report.extract_benchmark_features"),
        ]
        mocks = [item.start() for item in patches]
        self.addCleanup(lambda: [item.stop() for item in reversed(patches)])
        self.addCleanup(temporary.cleanup)
        report = run_stratify_report("", uploaded_video_path=str(path),
                                     local_source_type=source_type, no_network=True)
        return report, mocks

    def test_uploaded_and_cached_local_bypass_youtube_and_reuse_pipeline(self):
        for source_type in ("uploaded_file", "cached_local_clip"):
            with self.subTest(source_type=source_type):
                report, mocks = self._run_local(source_type)
                mocks[0].assert_not_called()
                mocks[1].assert_called_once()
                mocks[3].assert_not_called()
                self.assertIn(report["status"], {"success", "partial"})
                self.assertEqual(report["source_context"]["source_type"], source_type)
                self.assertEqual(report["benchmark_context_status"], "unavailable")

    def test_local_report_never_fabricates_metadata_or_benchmarks(self):
        report, _ = self._run_local("cached_local_clip")
        self.assertEqual(report["video"]["title"], "")
        self.assertEqual(report["video"]["channel_title"], "")
        self.assertIsNone(report["video"]["views"])
        self.assertEqual(report["benchmark"]["status"], "unavailable")
        self.assertFalse(report["benchmark"]["qualification"]["eligible_for_directional_learning"])
        self.assertIn("direct video evidence", " ".join(report["creator_report"]["limitations"]))

    @patch("core.stratify_report.get_full_youtube_context", side_effect=ValueError("Missing YOUTUBE_API_KEY"))
    def test_youtube_without_key_fails_clearly(self, context):
        report = run_stratify_report("https://www.youtube.com/watch?v=abcdefghijk")
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["stage"], "source_context_unavailable")
        self.assertIn("YOUTUBE_API_KEY", report["warnings"][0])

    def test_youtube_with_resolved_context_keeps_existing_path(self):
        data = {"video": {"video_id": "abcdefghijk", "title": "Trusted API title",
                          "channel_title": "Trusted API channel", "channel_id": "channel"},
                "channel": {}, "recent_videos": []}
        with patch("core.stratify_report.get_full_youtube_context", return_value=data) as context, \
             patch("core.stratify_report.analyze_intro_pipeline", return_value=successful_local_intro("clip.mp4")), \
             patch("core.stratify_report.understand_content", return_value={}), \
             patch("core.stratify_report.collect_benchmark_videos", return_value={
                 "shortlist": [], "qualification_diagnostics": []}), \
             patch("core.stratify_report.extract_benchmark_features", return_value=[]):
            report = run_stratify_report("https://www.youtube.com/watch?v=abcdefghijk")
        context.assert_called_once()
        self.assertIn(report["status"], {"success", "partial"})
        self.assertEqual(report["source_context"]["source_type"], "youtube_url")
        self.assertEqual(report["video"]["title"], "Trusted API title")

    def test_direct_evidence_can_continue_without_benchmark(self):
        report, _ = self._run_local()
        self.assertTrue(report.get("creator_report"))
        self.assertFalse(report["creator_report"]["evidence_validation"]["benchmark_supported"])
        self.assertLessEqual(len(report["creator_report"]["experiments"]), 3)

    def test_creator_mode_discloses_local_and_benchmark_limits(self):
        report, _ = self._run_local()
        with patch("ui.report.st") as st, patch("ui.report.render_card_grid"), \
             patch("ui.report.section_heading"), patch("ui.report.empty_state"), \
             patch("ui.report.render_advanced_analysis"):
            render_report(report, "creator", {})
        message = " ".join(str(call.args[0]) for call in st.info.call_args_list)
        self.assertIn("Local source analysis", message)
        self.assertIn("direct evidence", message)

    def test_creator_memory_schema_is_unchanged(self):
        self.assertEqual(SCHEMA_VERSION, 1)
