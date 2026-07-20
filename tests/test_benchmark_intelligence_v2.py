import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import benchmark_cache
from core.benchmark_collector import _cached_search_videos, collect_benchmark_videos
from core.benchmark_intelligence_v2 import (
    assess_benchmark_quality,
    qualify_neighborhood,
    select_performance_cohorts,
)
from core.category_intelligence import understand_category
from core.pattern_discovery import discover_patterns


def video(index, title, views, channel=None, duration=120):
    return {
        "video_id": str(index), "title": title, "description": "robot maze challenge",
        "views": views, "channel_title": channel or f"channel-{index}", "duration": duration,
        "matched_query": "robot maze challenge",
    }


class BenchmarkIntelligenceV2Tests(unittest.TestCase):
    def setUp(self):
        self.target = {"title": "Autonomous Robot Solves Giant Maze Challenge", "duration": 120}
        self.hypotheses = understand_category(self.target)["query_hypotheses"]

    def test_query_hypotheses_remove_packaging_and_explain_rank(self):
        result = understand_category({"title": "Official HD Autonomous Robot Solves Giant Maze Challenge"})
        self.assertNotIn("official", result["candidate_queries"][0].lower())
        self.assertTrue(result["query_hypotheses"][0]["retained_terms"])
        self.assertIn("official", [x.lower() for x in result["query_hypotheses"][0]["removed_weak_terms"]])

    def test_same_topic_retained_and_unrelated_high_view_rejected(self):
        items = [video(i, f"Autonomous Robot Solves Giant Maze Challenge episode {i}", 1000 * i) for i in range(1, 9)]
        items.append(video("x", "Celebrity Music Awards Red Carpet Highlights", 99_000_000))
        qualified, diagnostics = qualify_neighborhood(items, self.target, self.hypotheses)
        self.assertEqual(len(qualified), 8)
        self.assertNotIn("x", {x["video_id"] for x in qualified})
        self.assertGreater(diagnostics["rejected_candidate_count"], 0)

    def test_near_duplicate_titles_are_deduplicated(self):
        items = [video(i, f"Autonomous Robot Solves Giant Maze Challenge {i}", 1000 + i) for i in range(8)]
        items.append(video("copy", "Autonomous Robot Solves Giant Maze Challenge 1!", 5000))
        _, diagnostics = qualify_neighborhood(items, self.target, self.hypotheses)
        self.assertLess(diagnostics["deduplicated_count"], len(items))

    def test_channel_balance_and_credible_lower_group(self):
        views = [100, 180, 300, 600, 1200, 3000, 7000, 15000, 30000, 70000]
        items = [video(i, "Autonomous Robot Solves Giant Maze Challenge", value, "dominant" if i < 7 else f"alt-{i}") for i, value in enumerate(views)]
        top, lower, diagnostics = select_performance_cohorts(items)
        self.assertGreaterEqual(len(top), 3)
        self.assertGreaterEqual(len(lower), 3)
        self.assertLessEqual(max([x["channel_title"] for x in top].count(c) for c in {x["channel_title"] for x in top}), 2)
        self.assertTrue(all(item["views"] >= 10 for item in lower))
        self.assertAlmostEqual(diagnostics["median_view_ratio"], diagnostics["top_median_views"] / diagnostics["lower_median_views"], places=3)

    def test_adaptive_threshold_never_falls_below_safe_floor(self):
        items = [video(i, f"Robot Maze Challenge test {i}", 1000 + i) for i in range(5)]
        _, diagnostics = qualify_neighborhood(items, self.target, self.hypotheses, minimum=8)
        self.assertGreaterEqual(diagnostics["relevance_threshold_used"], 48)
        self.assertIn("relaxed", diagnostics["relevance_threshold_reason"].lower())

    def test_quality_distinguishes_weak_and_strong_learning(self):
        strong = [video(i, "Autonomous Robot Solves Giant Maze Challenge", 100 * (2 ** i)) for i in range(10)]
        top, lower, perf = select_performance_cohorts(strong)
        perf.update({"channel_coverage": 8, "query_coverage": ["a", "b", "c"], "benchmark_quality_warnings": []})
        quality = assess_benchmark_quality(strong, top, lower, perf, 1.0)
        self.assertTrue(quality["eligible_for_directional_learning"])
        weak = assess_benchmark_quality(strong[:2], [], [], {"benchmark_quality_warnings": []}, 0.0)
        self.assertFalse(weak["eligible_for_directional_learning"])
        self.assertIn("coherent_performance_groups_unavailable", weak["failure_reasons"])

    def test_patterns_require_three_observations_per_group(self):
        top = [{"feature_summary": {"opening": "action"}}] * 2
        lower = [{"feature_summary": {"opening": "text"}}] * 2
        result = discover_patterns(top, lower, {"feature_summary": {"opening": "text"}}, min_support=3)
        self.assertEqual(result["recommendations"], [])
        top.append({"feature_summary": {"opening": "action"}})
        lower.append({"feature_summary": {"opening": "text"}})
        result = discover_patterns(top, lower, {"feature_summary": {"opening": "text"}}, min_support=3)
        self.assertTrue(result["recommendations"])

    def test_single_multiple_and_abstaining_pattern_reports_are_safe(self):
        user = {"feature_summary": {"opening": "text", "pacing": "slow"}}
        single = discover_patterns(
            [{"feature_summary": {"opening": "action"}}] * 3,
            [{"feature_summary": {"opening": "text"}}] * 3,
            user, min_support=3,
        )
        self.assertEqual(len(single["recommendations"]), 1)
        multiple = discover_patterns(
            [{"feature_summary": {"opening": "action", "pacing": "fast"}}] * 3,
            [{"feature_summary": {"opening": "text", "pacing": "slow"}}] * 3,
            user, min_support=3,
        )
        self.assertGreaterEqual(len(multiple["recommendations"]), 2)
        abstain = discover_patterns([], [], user, min_support=3)
        self.assertEqual(abstain["recommendations"], [])

    def test_search_failure_uses_cache_and_expiry_is_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cache.json"
            with patch("core.benchmark_cache.cache_path", return_value=path):
                benchmark_cache.write("robot maze", 15, [video(1, "Robot Maze", 100)])
                with patch("core.benchmark_collector.search_videos", side_effect=RuntimeError("quota")):
                    results, error, info = _cached_search_videos("robot maze", 15)
                self.assertEqual(len(results), 1)
                self.assertEqual(error, "quota")
                self.assertTrue(info["cached_evidence_used"])
                benchmark_cache.write("robot maze", 15, results, now=100)
                expired, info = benchmark_cache.read("robot maze", 15, ttl_seconds=5, now=106)
                self.assertIsNone(expired)
                self.assertEqual(info["status"], "expired")

    def test_collector_count_schema_is_truthful_and_compatible(self):
        results = [video(i, f"Autonomous Robot Solves Giant Maze Challenge episode {i}", 1000 * i) for i in range(1, 9)]
        category = understand_category(self.target)
        with patch("core.benchmark_collector._cached_search_videos", return_value=(results, None, {"status": "fresh", "cached_evidence_used": False})):
            report = collect_benchmark_videos(category, user_video=self.target)
        for key in ("query", "benchmark_anchor", "candidate_count", "merged_candidate_count", "cleaned_count", "top_performers", "lower_performers", "all_candidates"):
            self.assertIn(key, report)
        self.assertEqual(report["candidate_count"], report["qualified_candidate_count"])
        self.assertEqual(report["merged_candidate_count"], report["deduplicated_count"])

    def test_report_and_ui_imports_remain_compatible(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec("core.stratify_report"))
        self.assertIsNotNone(importlib.util.find_spec("app"))


if __name__ == "__main__":
    unittest.main()
