import unittest
from unittest.mock import patch

from core.benchmark_qualification import qualify_observed_benchmarks


def _understanding(job, promise, temporal):
    return {
        "narrative_draft": {
            "main_subject": job,
            "opening_goal": promise,
            "viewer_expectation": promise,
            "story_promise": promise,
            "narrative_progression": temporal,
        },
        "temporal": {"summary": temporal},
        "events": {"events": [{"event_type": "change"}, {"event_type": "reveal"}]},
    }


def _observed(video_id, views, job="a live challenge", promise="watch the challenge unfold"):
    return {
        "status": "success",
        "video": {
            "video_id": video_id,
            "title": f"{job} highlight {video_id}",
            "description": promise,
            "duration": 120,
            "views": views,
            "channel_title": f"channel-{video_id}",
        },
        "vision": {
            "frame_observations": [
                {"visual_energy": "high", "human_presence": True},
                {"visual_energy": "high", "human_presence": True},
            ],
            "visual_energy": "high",
            "human_presence": True,
        },
        "understanding": _understanding(job, promise, "action develops through visible events"),
        "features": {"feature_summary": {"pacing": "fast", "opening_mode": "action"}},
        "content_identity": {
            "subject": job,
            "viewer_intent": promise,
            "presentation_style": "events shown directly",
            "storytelling_format": "the event unfolds through visible action",
            "source_context": "the uploader presents the recorded event",
        },
    }


class BenchmarkQualificationTests(unittest.TestCase):
    def setUp(self):
        self.user_video = {
            "video_id": "user",
            "title": "a live challenge highlight",
            "description": "watch the challenge unfold",
            "duration": 118,
        }
        self.user_vision = {
            "frame_observations": [
                {"visual_energy": "high", "human_presence": True},
                {"visual_energy": "high", "human_presence": True},
            ],
            "visual_energy": "high",
            "human_presence": True,
        }
        self.user_understanding = _understanding(
            "a live challenge",
            "watch the challenge unfold",
            "action develops through visible events",
        )
        self.user_features = {"feature_summary": {"pacing": "fast", "opening_mode": "action"}}
        self.user_identity = {
            "subject": "a live challenge",
            "viewer_intent": "watch the challenge unfold",
            "presentation_style": "events shown directly",
            "storytelling_format": "the event unfolds through visible action",
            "source_context": "the uploader presents the recorded event",
        }

    @patch("core.benchmark_qualification.compare_viewer_jobs")
    def test_groups_are_formed_only_from_observed_compatible_candidates(self, semantic_compare):
        semantic_compare.side_effect = lambda reference, candidate: {
            "status": "success",
            "same_viewing_job": candidate.get("viewer_intent") == reference.get("viewer_intent"),
            "reason": "Viewer intent differs." if candidate.get("viewer_intent") != reference.get("viewer_intent") else "Compatible.",
        }
        compatible = [_observed(str(index), views) for index, views in enumerate([100, 300, 900, 2700], 1)]
        adjacent = _observed(
            "adjacent",
            50000,
            job="a narrated industry analysis",
            promise="understand the business history and critical response",
        )
        metadata_only = {
            "status": "failed",
            "video": {"video_id": "metadata", "title": self.user_video["title"], "views": 999999},
        }

        result = qualify_observed_benchmarks(
            self.user_video,
            self.user_vision,
            self.user_understanding,
            self.user_features,
            compatible + [adjacent, metadata_only],
            self.user_identity,
        )

        self.assertEqual(result["status"], "success")
        selected = {
            item["video"]["video_id"]
            for item in result["top_performers"] + result["lower_performers"]
        }
        self.assertNotIn("adjacent", selected)
        self.assertNotIn("metadata", selected)
        diagnostics = {item["video_id"]: item for item in result["diagnostics"]}
        self.assertEqual(diagnostics["metadata"]["evidence_mode"], "metadata_only")
        self.assertEqual(diagnostics["adjacent"]["qualification_status"], "rejected")
        self.assertIn("Viewer intent", diagnostics["adjacent"]["rejection_reason"])

    @patch("core.benchmark_qualification.compare_viewer_jobs")
    def test_incoherent_or_small_neighborhood_returns_limited(self, semantic_compare):
        semantic_compare.return_value = {
            "status": "success", "same_viewing_job": True, "reason": "Compatible."
        }
        result = qualify_observed_benchmarks(
            self.user_video,
            self.user_vision,
            self.user_understanding,
            self.user_features,
            [_observed("one", 100), _observed("two", 1000)],
            self.user_identity,
        )
        self.assertEqual(result["status"], "limited")
        self.assertEqual(result["top_performers"], [])
        self.assertEqual(result["lower_performers"], [])


if __name__ == "__main__":
    unittest.main()
