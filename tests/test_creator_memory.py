import json
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from core.memory.aggregator import MIN_STABLE_ANALYSES, aggregate
from core.memory.comparison import compare_current
from core.memory.models import AnalysisRecord, Experiment, VideoProject
from core.memory.schema import SCHEMA_VERSION, UnsupportedSchemaVersion, connect
from core.memory.serialization import normalize_report, source_identity, stable_json
from core.memory.service import CreatorMemoryService
from stratify_platform.projects import create_project


def report(strategy="subject-first", focus="person", progression="single phase",
           text="visual_only", experiments=1, status="success"):
    items = [{
        "structural_dimension": f"dimension_{index}", "hypothesis": "A controlled change",
        "change": "Change the first phase", "what_stays_constant": "Everything else",
        "version_a": "Current", "version_b": "Alternative", "confidence": "moderate",
        "limitation": "No outcome evidence.",
    } for index in range(experiments)]
    return {
        "status": status, "analysis_version": "test-v1", "video": {"title": "Test video"},
        "creative_structure": {"opening_strategy": strategy, "structural_rhythm": progression, "reveal_pattern": "anchor established immediately"},
        "creative_understanding": {"summary": "A direct opening."},
        "semantic_observation": {
            "primary_visual_focus": focus, "subject_presence_pattern": "single_subject",
            "information_mode": text, "text_evidence_confidence": "moderate",
        },
        "creator_report": {
            "report_version": "creator-product-v1", "opening_snapshot": {"summary": "A direct opening."},
            "creative_reasoning_status": "success", "biggest_opportunity": {
                "supported": bool(experiments), "confidence": "moderate",
                "limitation": "No performance outcome is available.",
            }, "experiments": items,
            "confidence_summary": {
                "analysis_completeness": "complete", "evidence_confidence": "moderate",
                "recommendation_confidence": "moderate", "text_evidence": "moderate",
            },
        },
    }


def record(index, strategy="subject-first", focus="person", text="visual_only"):
    value = normalize_report(report(strategy, focus, text=text))
    value.update({"id": str(index), "video_id": f"v{index}", "created_at": f"2026-01-{index + 1:02d}T00:00:00+00:00"})
    return AnalysisRecord(**value)


class CreatorMemoryDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "memory.db"
        self.service = CreatorMemoryService(self.path, now=lambda: "2026-01-01T00:00:00+00:00")

    def tearDown(self):
        self.temp.cleanup()

    def test_schema_initializes_idempotently_with_foreign_keys(self):
        CreatorMemoryService(self.path, now=lambda: "2026-01-02T00:00:00+00:00")
        connection = connect(self.path)
        try:
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT schema_version FROM memory_metadata").fetchone()[0], SCHEMA_VERSION)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM memory_metadata").fetchone()[0], 1)
        finally:
            connection.close()

    def test_future_schema_fails_safely(self):
        connection = connect(self.path)
        try:
            with connection:
                connection.execute("UPDATE memory_metadata SET schema_version=999")
        finally:
            connection.close()
        with self.assertRaises(UnsupportedSchemaVersion):
            CreatorMemoryService(self.path)

    def test_profile_create_and_update(self):
        first = self.service.save_profile("Creator", "Channel", niche="Education")
        second = self.service.save_profile("Updated", "Channel 2", creator_id=first["id"], channel_id=first["channel_id"])
        self.assertEqual(second["display_name"], "Updated")
        self.assertEqual(second["channel_name"], "Channel 2")

    def test_save_revision_duplicate_history_and_cascade_delete(self):
        self.service.save_profile("Creator", "Channel")
        project = create_project(source_url="https://youtube.com/watch?v=abc123", title="Project")
        one = self.service.save_report(report(), project)
        two = self.service.save_report(report(strategy="context-first"), project)
        self.assertEqual(one["video_id"], two["video_id"])
        data = self.service.dashboard()
        self.assertEqual(data["counts"], {"videos": 1, "analyses": 2})
        self.assertEqual(data["history"][0]["revision_count"], 2)
        self.service.delete_project(one["video_id"])
        self.assertEqual(self.service.dashboard()["counts"], {"videos": 0, "analyses": 0})

    def test_experiments_save_and_update_without_inferred_outcome(self):
        self.service.save_profile("Creator", "Channel")
        saved = self.service.save_report(report(experiments=2), create_project(upload_name="clip.mp4"))
        items = self.service.dashboard()["experiments"]
        self.assertEqual(len(items), 2)
        self.assertTrue(all(item.status == "suggested" and not item.result_summary for item in items))
        self.service.update_experiment(items[0].id, status="completed", result_summary="Entered by creator")
        updated = self.service.dashboard()["experiments"][0]
        self.assertEqual(updated.status, "completed")
        self.assertEqual(updated.result_summary, "Entered by creator")

    def test_transaction_rolls_back_analysis_when_experiment_invalid(self):
        profile = self.service.save_profile("Creator", "Channel")
        timestamp = "2026-01-01T00:00:00+00:00"
        video = VideoProject("video", profile["channel_id"], "video_upload", "success", timestamp, timestamp)
        video_id, _ = self.service.repository.resolve_video(video)
        value = normalize_report(report())
        value.update({"id": "analysis", "video_id": video_id, "created_at": timestamp})
        analysis = AnalysisRecord(**value)
        invalid = Experiment(
            "experiment", "analysis", video_id, "dimension", "hypothesis", "change", "constant",
            "a", "b", "moderate", "limitation", "not-a-supported-status", timestamp, timestamp,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.service.repository.save_analysis_with_experiments(analysis, [invalid])
        self.assertEqual(self.service.dashboard()["counts"]["analyses"], 0)

    def test_export_is_structured_and_validated(self):
        self.service.save_profile("Creator", "Channel")
        self.service.save_report(report(), create_project(upload_name="clip.mp4"))
        payload = json.loads(self.service.export_json())
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertEqual(len(payload["videos"]), 1)
        self.assertNotIn("raw_video", str(payload))
        self.assertTrue(self.service.validate_export(payload))


class CreatorMemorySerializationTests(unittest.TestCase):
    def test_stable_serialization_and_missing_fields(self):
        self.assertEqual(stable_json({"b": 1, "a": 2}), '{"a":2,"b":1}')
        value = normalize_report({})
        self.assertIsNone(value["opening_strategy"])
        self.assertEqual(value["experiments"], [])
        self.assertEqual(value["recommendation_state"], "abstained")

    def test_limited_text_and_abstention_are_preserved(self):
        value = report(text="text_supported", experiments=0)
        value["creator_report"]["confidence_summary"]["text_evidence"] = "limited"
        normalized = normalize_report(value)
        self.assertEqual(normalized["written_information_state"], "limited")
        self.assertEqual(normalized["recommendation_state"], "abstained")

    def test_source_identity_uses_ids_not_titles(self):
        first = source_identity("https://youtu.be/abc123")
        second = source_identity("https://www.youtube.com/watch?v=abc123")
        self.assertEqual(first["external_video_id"], second["external_video_id"])
        self.assertNotEqual(source_identity(upload_name="a.mp4")["source_fingerprint"],
                            source_identity(upload_name="b.mp4")["source_fingerprint"])


class CreatorMemoryAggregationTests(unittest.TestCase):
    def test_zero_one_and_two_analysis_states(self):
        self.assertEqual(aggregate([])["confidence"], "insufficient_history")
        self.assertEqual(aggregate([record(0)])["patterns"]["opening_strategy"]["state"], "insufficient_history")
        self.assertEqual(aggregate([record(0), record(1)])["patterns"]["opening_strategy"]["state"], "emerging_pattern")

    def test_consistent_history_becomes_repeated(self):
        result = aggregate([record(i) for i in range(MIN_STABLE_ANALYSES)])
        self.assertEqual(result["patterns"]["opening_strategy"]["state"], "repeated_pattern")
        self.assertEqual(result["confidence"], "moderate")

    def test_contradictions_lower_confidence(self):
        values = [record(0), record(1), record(2, "context-first"), record(3, "context-first")]
        result = aggregate(values)
        self.assertEqual(result["patterns"]["opening_strategy"]["state"], "mixed_pattern")
        self.assertEqual(result["confidence"], "limited")

    def test_unknown_and_limited_values_are_excluded(self):
        values = [replace(record(0), opening_strategy=None, written_information_state="limited"), record(1)]
        result = aggregate(values)
        self.assertEqual(result["patterns"]["opening_strategy"]["observations"], 1)
        self.assertEqual(result["patterns"]["written_information_state"]["observations"], 1)

    def test_experiment_dimensions_track_unexplored(self):
        class Item:
            dimension = "visual_anchor"
        result = aggregate([], [Item()])
        self.assertNotIn("visual_anchor", result["unexplored_experiment_dimensions"])


class CreatorMemoryComparisonTests(unittest.TestCase):
    def test_insufficient_and_limited(self):
        self.assertEqual(compare_current(record(0), [])["state"], "insufficient_history")
        limited = replace(record(0), opening_strategy=None, primary_visual_focus=None,
                          progression_style=None, subject_timing=None, subject_presence=None,
                          multiple_subjects=None, written_information_state="limited", recommendation_state=None)
        self.assertEqual(compare_current(limited, [record(1), record(2)])["state"], "evidence_too_limited")

    def test_match_partial_difference_and_new(self):
        baseline = [record(0), record(1), record(2)]
        self.assertEqual(compare_current(record(4), baseline)["state"], "matches_typical_pattern")
        partial = replace(record(4), opening_strategy="context-first")
        self.assertEqual(compare_current(partial, baseline)["state"], "newly_observed_pattern")
        known_mixed = [record(0), record(1, "context-first"), record(2)]
        current = replace(record(4), opening_strategy="context-first", primary_visual_focus="object")
        self.assertEqual(compare_current(current, known_mixed)["state"], "newly_observed_pattern")

    def test_current_is_not_added_to_baseline(self):
        baseline = [record(0), record(1)]
        result = compare_current(record(3, "context-first"), baseline)
        self.assertEqual(result["evidence"]["baseline_analyses"], 2)


if __name__ == "__main__":
    unittest.main()
