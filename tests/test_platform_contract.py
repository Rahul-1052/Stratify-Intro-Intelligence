import unittest
from stratify_platform.contracts import IntelligenceStage, ModuleStatus
from stratify_platform.module_registry import get_module, list_modules, run_module
from stratify_platform.projects import create_project, restore_project


class PlatformContractTests(unittest.TestCase):
    def test_intro_intelligence_is_registered_and_available(self):
        module = get_module("intro_intelligence")
        self.assertTrue(module.is_available)
        self.assertEqual(module.status, ModuleStatus.AVAILABLE)
        self.assertIn("youtube_url", module.supported_inputs)
        self.assertEqual(module.stages[0], IntelligenceStage.ACQUIRE)
        self.assertEqual(module.stages[-1], IntelligenceStage.PRESENT)

    def test_future_modules_are_planned_and_cannot_run(self):
        future = [module for module in list_modules() if module.module_id != "intro_intelligence"]
        self.assertEqual(len(future), 5)
        for module in future:
            self.assertEqual(module.status, ModuleStatus.PLANNED)
            self.assertFalse(module.is_available)
            self.assertIsNone(module.runner)
            self.assertEqual(module.capabilities, ())
            with self.assertRaisesRegex(RuntimeError, "cannot be run"):
                run_module(module.module_id, url="unused")

    def test_project_round_trip_restores_module_result_and_experiments(self):
        project = create_project(
            source_url="https://youtube.com/watch?v=example",
            upload_name="opening.mp4",
            title="A creator project",
        )
        result = {
            "status": "success",
            "creator_report": {"experiments": [{"title": "Test the first frame"}]},
        }
        project.record_result("intro_intelligence", result)
        restored = restore_project(project.to_session())
        self.assertEqual(restored.project_id, project.project_id)
        self.assertEqual(restored.module_results["intro_intelligence"], result)
        self.assertEqual(restored.experiments[0]["title"], "Test the first frame")
        self.assertEqual(restored.module_run_statuses["intro_intelligence"], "success")

    def test_invalid_session_state_does_not_create_a_project(self):
        self.assertIsNone(restore_project(None))
        self.assertIsNone(restore_project("corrupt"))


if __name__ == "__main__":
    unittest.main()
