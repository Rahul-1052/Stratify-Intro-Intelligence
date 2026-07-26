"""SQLite schema and deliberately small migration boundary."""

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1


class UnsupportedSchemaVersion(RuntimeError):
    pass


DDL = """
CREATE TABLE IF NOT EXISTS memory_metadata (
  singleton INTEGER PRIMARY KEY CHECK(singleton=1), schema_version INTEGER NOT NULL,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS creators (
  id TEXT PRIMARY KEY, display_name TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '',
  primary_creator INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS channels (
  id TEXT PRIMARY KEY, creator_id TEXT NOT NULL REFERENCES creators(id) ON DELETE CASCADE,
  platform TEXT NOT NULL, external_channel_id TEXT, channel_name TEXT NOT NULL,
  channel_url TEXT, niche TEXT, notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS videos (
  id TEXT PRIMARY KEY, channel_id TEXT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
  external_video_id TEXT, source_url TEXT, title TEXT, created_at TEXT NOT NULL, analyzed_at TEXT NOT NULL,
  source_type TEXT NOT NULL, analysis_status TEXT NOT NULL, published_at TEXT, thumbnail_url TEXT,
  duration_seconds REAL, source_fingerprint TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS videos_external_unique
  ON videos(channel_id, external_video_id) WHERE external_video_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS videos_fingerprint_unique
  ON videos(channel_id, source_fingerprint) WHERE source_fingerprint IS NOT NULL;
CREATE TABLE IF NOT EXISTS analyses (
  id TEXT PRIMARY KEY, video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  analysis_version TEXT NOT NULL, created_at TEXT NOT NULL, snapshot_json TEXT NOT NULL,
  creative_structure_json TEXT NOT NULL, creative_understanding_json TEXT NOT NULL,
  reasoning_summary_json TEXT NOT NULL, opportunity_json TEXT NOT NULL, experiments_json TEXT NOT NULL,
  confidence_summary_json TEXT NOT NULL, evidence_limitations_json TEXT NOT NULL,
  analysis_completeness TEXT NOT NULL, opening_strategy TEXT, primary_visual_focus TEXT,
  progression_style TEXT, subject_timing TEXT, subject_presence TEXT, multiple_subjects INTEGER,
  written_information_state TEXT, recommendation_state TEXT, recommendation_confidence TEXT
);
CREATE TABLE IF NOT EXISTS experiments (
  id TEXT PRIMARY KEY, analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
  video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE, dimension TEXT NOT NULL,
  hypothesis TEXT NOT NULL, change_description TEXT NOT NULL, keep_constant TEXT NOT NULL,
  version_a TEXT NOT NULL, version_b TEXT NOT NULL, confidence TEXT NOT NULL, limitation TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('suggested','planned','running','completed','rejected','archived')),
  result_summary TEXT NOT NULL DEFAULT '', creator_notes TEXT NOT NULL DEFAULT '',
  started_at TEXT, completed_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS analyses_video_created ON analyses(video_id, created_at DESC);
CREATE INDEX IF NOT EXISTS experiments_status ON experiments(status, updated_at DESC);
"""


def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(connection, now):
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_metadata'"
    ).fetchone()
    if row:
        version = connection.execute(
            "SELECT schema_version FROM memory_metadata WHERE singleton=1"
        ).fetchone()
        if version and version["schema_version"] > SCHEMA_VERSION:
            raise UnsupportedSchemaVersion(
                f"Creator Memory schema {version['schema_version']} is newer than supported schema {SCHEMA_VERSION}."
            )
    with connection:
        connection.executescript(DDL)
        connection.execute(
            """INSERT INTO memory_metadata(singleton,schema_version,created_at,updated_at)
               VALUES(1,?,?,?) ON CONFLICT(singleton) DO UPDATE SET updated_at=excluded.updated_at""",
            (SCHEMA_VERSION, now, now),
        )
