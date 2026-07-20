import unittest

from streamlit.testing.v1 import AppTest

from stratify_platform.projects import create_project


def _project_with_observation_report():
    project = create_project(source_url="https://youtube.com/watch?v=offline", title="Offline creator project")
    report = {
        "status": "success", "warnings": [], "video": {"title": project.title},
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
        self.assertIn("Planned", landing)

        app.session_state["stratify_project"] = _project_with_observation_report()
        app.run(timeout=15)
        self.assertEqual(len(app.exception), 0)
        project_view = " ".join(item.value for item in app.markdown)
        self.assertIn("Offline creator project", project_view)
        headings = [item.value for item in app.header]
        self.assertIn("Opening Snapshot", headings)
        self.assertIn("Three Observation-Backed Experiments", headings)


if __name__ == "__main__":
    unittest.main()
