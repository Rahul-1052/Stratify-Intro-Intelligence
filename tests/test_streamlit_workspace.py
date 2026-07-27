import unittest
import os
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from stratify_platform.projects import create_project


def _project_with_observation_report(warnings=None):
    project = create_project(source_url="https://youtube.com/watch?v=offline", title="Offline creator project")
    report = {
        "status": "success", "warnings": warnings or [], "video": {"title": project.title},
        "intro_observation": {"status": "success", "observation": {"opening_summary": "A creator appears in a bright room.", "hook_type": "direct address"}},
        "feature_report": {"feature_summary": {"pacing": "moderate"}},
        "vision": {"frame_observations": [{"timestamp": 0, "human_presence": True, "visual_energy": "moderate"}]},
        "patterns": {}, "benchmark": {}, "reasoning": {}, "evidence": {},
    }
    project.record_result("intro_intelligence", report)
    return project.to_session()


class StreamlitWorkspaceTests(unittest.TestCase):
    def test_landing_and_restored_project_render_without_errors(self):
        app = AppTest.from_file("app.py")
        app.run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        landing = " ".join(item.value for item in app.markdown)
        self.assertIn("Creative Intelligence Platform", landing)
        self.assertIn("Intro Intelligence", landing)
        self.assertIn("Story Intelligence", landing)
        self.assertIn("Coming later", [item.label for item in app.expander])
        self.assertIn("Creator Memory", landing)

        app.session_state["stratify_project"] = _project_with_observation_report()
        app.run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        project_view = " ".join(item.value for item in app.markdown)
        self.assertIn("Offline creator project", project_view)
        headings = [item.value for item in app.header]
        self.assertIn("Hero Summary", headings)
        self.assertIn("Primary Experiment", headings)

    def test_creator_fallback_message_hides_internal_warning(self):
        app = AppTest.from_file("app.py")
        app.session_state["stratify_project"] = _project_with_observation_report([
            "yt_dlp_download_failed: HTTP ERROR 403 internal downloader detail"
        ])
        with patch.dict(os.environ, {"STRATIFY_PRODUCT_MODE": "creator"}):
            app.run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        visible = " ".join(item.value for item in [*app.warning, *app.info])
        self.assertIn("Automatic video access was unavailable", visible)
        self.assertNotIn("yt_dlp", visible)


if __name__ == "__main__":
    unittest.main()
