import json
from contextlib import contextmanager
from dataclasses import fields

from core.memory.models import AnalysisRecord, Channel, Creator, Experiment, VideoProject
from core.memory.schema import connect, initialize
from core.memory.serialization import stable_json

JSON_COLUMNS = {
    "snapshot": "snapshot_json", "creative_structure": "creative_structure_json",
    "creative_understanding": "creative_understanding_json", "reasoning_summary": "reasoning_summary_json",
    "opportunity": "opportunity_json", "experiments": "experiments_json",
    "confidence_summary": "confidence_summary_json", "evidence_limitations": "evidence_limitations_json",
}


class MemoryRepository:
    def __init__(self, path, now):
        self.path, self.now = path, now
        with self.connection() as connection:
            initialize(connection, now())

    @contextmanager
    def connection(self):
        connection = connect(self.path)
        try:
            yield connection
        finally:
            connection.close()

    def _write(self, sql, values):
        with self.connection() as connection, connection:
            connection.execute(sql, values)

    def save_creator(self, item):
        self._write("""INSERT INTO creators(id,display_name,notes,primary_creator,created_at,updated_at)
          VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET display_name=excluded.display_name,
          notes=excluded.notes,primary_creator=excluded.primary_creator,updated_at=excluded.updated_at""",
          (item.id,item.display_name,item.notes,int(item.primary_creator),item.created_at,item.updated_at))

    def save_channel(self, item):
        self._write("""INSERT INTO channels(id,creator_id,platform,external_channel_id,channel_name,channel_url,niche,notes,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET platform=excluded.platform,
          external_channel_id=excluded.external_channel_id,channel_name=excluded.channel_name,
          channel_url=excluded.channel_url,niche=excluded.niche,notes=excluded.notes,updated_at=excluded.updated_at""",
          (item.id,item.creator_id,item.platform,item.external_channel_id,item.channel_name,item.channel_url,item.niche,item.notes,item.created_at,item.updated_at))

    def primary_profile(self):
        with self.connection() as connection:
            row = connection.execute("""SELECT c.*,ch.id channel_id,ch.platform,ch.external_channel_id,
              ch.channel_name,ch.channel_url,ch.niche,ch.notes channel_notes,ch.created_at channel_created_at,
              ch.updated_at channel_updated_at FROM creators c LEFT JOIN channels ch ON ch.creator_id=c.id
              WHERE c.primary_creator=1 ORDER BY c.created_at,ch.created_at LIMIT 1""").fetchone()
        return dict(row) if row else None

    def resolve_video(self, item):
        with self.connection() as connection, connection:
            row = None
            if item.external_video_id:
                row = connection.execute("SELECT * FROM videos WHERE channel_id=? AND external_video_id=?", (item.channel_id,item.external_video_id)).fetchone()
            elif item.source_fingerprint:
                row = connection.execute("SELECT * FROM videos WHERE channel_id=? AND source_fingerprint=?", (item.channel_id,item.source_fingerprint)).fetchone()
            if row:
                connection.execute("""UPDATE videos SET title=COALESCE(?,title),source_url=COALESCE(?,source_url),
                  analyzed_at=?,analysis_status=? WHERE id=?""", (item.title,item.source_url,item.analyzed_at,item.analysis_status,row["id"]))
                return row["id"], "existing_project_new_revision"
            connection.execute("""INSERT INTO videos(id,channel_id,external_video_id,source_url,title,created_at,analyzed_at,
              source_type,analysis_status,published_at,thumbnail_url,duration_seconds,source_fingerprint)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                item.id,item.channel_id,item.external_video_id,item.source_url,item.title,item.created_at,
                item.analyzed_at,item.source_type,item.analysis_status,item.published_at,item.thumbnail_url,
                item.duration_seconds,item.source_fingerprint,
              ))
            return item.id, "new_project"

    def save_analysis_with_experiments(self, analysis, experiments):
        columns = [field.name for field in fields(AnalysisRecord)]
        db_columns = [JSON_COLUMNS.get(item, item) for item in columns]
        values = [stable_json(getattr(analysis, item)) if item in JSON_COLUMNS else
                  int(getattr(analysis, item)) if item == "multiple_subjects" and getattr(analysis,item) is not None else
                  getattr(analysis, item) for item in columns]
        with self.connection() as connection, connection:
            connection.execute(f"INSERT INTO analyses({','.join(db_columns)}) VALUES({','.join('?' for _ in values)})", values)
            for item in experiments:
                names = [field.name for field in fields(Experiment)]
                connection.execute(f"INSERT INTO experiments({','.join(names)}) VALUES({','.join('?' for _ in names)})",
                                   [getattr(item, name) for name in names])

    def analyses_for_creator(self, creator_id):
        with self.connection() as connection:
            rows = connection.execute("""SELECT a.* FROM analyses a JOIN videos v ON v.id=a.video_id
              JOIN channels ch ON ch.id=v.channel_id WHERE ch.creator_id=? ORDER BY a.created_at""", (creator_id,)).fetchall()
        result, errors = [], []
        for row in rows:
            try:
                result.append(self._analysis_from_row(row))
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                errors.append({"analysis_id": row["id"], "error": str(exc)})
        return result, errors

    @staticmethod
    def _analysis_from_row(row):
        value = dict(row)
        for key, column in JSON_COLUMNS.items():
            value[key] = json.loads(value.pop(column))
        value["multiple_subjects"] = None if value["multiple_subjects"] is None else bool(value["multiple_subjects"])
        return AnalysisRecord(**value)

    def analysis_for_reopen(self, analysis_id):
        with self.connection() as connection:
            row = connection.execute(
                """SELECT a.*,v.title video_title,v.source_type video_source_type,
                   (SELECT COUNT(*) FROM analyses prior WHERE prior.video_id=a.video_id
                    AND (prior.created_at<a.created_at OR
                    (prior.created_at=a.created_at AND prior.rowid<=a.rowid))) revision
                   FROM analyses a JOIN videos v ON v.id=a.video_id WHERE a.id=?""",
                (analysis_id,),
            ).fetchone()
        if not row:
            return None, {"analysis_id": analysis_id, "error": "missing_analysis"}
        metadata = {
            "title": row["video_title"], "source_type": row["video_source_type"],
            "revision": row["revision"],
        }
        analysis_columns = {
            key: row[key] for key in row.keys()
            if key not in {"video_title", "video_source_type", "revision"}
        }
        try:
            return self._analysis_from_row(analysis_columns), metadata
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return None, {**metadata, "analysis_id": analysis_id, "error": str(exc)}

    def revisions_for_video(self, video_id):
        with self.connection() as connection:
            return [dict(row) for row in connection.execute(
                """SELECT id,created_at,analysis_version,analysis_completeness,
                   ROW_NUMBER() OVER (ORDER BY created_at,id) revision
                   FROM analyses WHERE video_id=? ORDER BY created_at DESC,id DESC""",
                (video_id,),
            ).fetchall()]

    def experiments_for_creator(self, creator_id):
        with self.connection() as connection:
            rows = connection.execute("""SELECT e.* FROM experiments e JOIN videos v ON v.id=e.video_id
              JOIN channels ch ON ch.id=v.channel_id WHERE ch.creator_id=? ORDER BY e.updated_at DESC""", (creator_id,)).fetchall()
        return [Experiment(**dict(row)) for row in rows]

    def history(self, creator_id):
        with self.connection() as connection:
            history = [dict(row) for row in connection.execute("""SELECT v.*,COUNT(DISTINCT a.id) revision_count,
              COUNT(DISTINCT e.id) experiment_count,MAX(a.created_at) latest_analysis_at,
              (SELECT opening_strategy FROM analyses la WHERE la.video_id=v.id ORDER BY la.created_at DESC LIMIT 1) opening_strategy,
              (SELECT primary_visual_focus FROM analyses la WHERE la.video_id=v.id ORDER BY la.created_at DESC LIMIT 1) primary_visual_focus,
              (SELECT recommendation_state FROM analyses la WHERE la.video_id=v.id ORDER BY la.created_at DESC LIMIT 1) recommendation_state,
              (SELECT recommendation_confidence FROM analyses la WHERE la.video_id=v.id ORDER BY la.created_at DESC LIMIT 1) recommendation_confidence,
              (SELECT analysis_completeness FROM analyses la WHERE la.video_id=v.id ORDER BY la.created_at DESC LIMIT 1) analysis_completeness
              FROM videos v JOIN channels ch ON ch.id=v.channel_id LEFT JOIN analyses a ON a.video_id=v.id
              LEFT JOIN experiments e ON e.video_id=v.id WHERE ch.creator_id=? GROUP BY v.id
              ORDER BY latest_analysis_at DESC""", (creator_id,)).fetchall()]
        for item in history:
            item["revisions"] = self.revisions_for_video(item["id"])
        return history

    def update_experiment(self, experiment_id, **updates):
        allowed = {"status","creator_notes","result_summary","started_at","completed_at"}
        values = {key: value for key, value in updates.items() if key in allowed}
        if not values:
            return
        values["updated_at"] = self.now()
        self._write(f"UPDATE experiments SET {','.join(f'{key}=?' for key in values)} WHERE id=?",
                    (*values.values(), experiment_id))

    def delete_analysis(self, analysis_id):
        self._write("DELETE FROM analyses WHERE id=?", (analysis_id,))

    def delete_project(self, video_id):
        self._write("DELETE FROM videos WHERE id=?", (video_id,))

    def reset_creator(self, creator_id):
        self._write("DELETE FROM creators WHERE id=?", (creator_id,))

    def counts(self, creator_id):
        with self.connection() as connection:
            row = connection.execute("""SELECT COUNT(DISTINCT v.id) videos,COUNT(DISTINCT a.id) analyses
              FROM channels ch LEFT JOIN videos v ON v.channel_id=ch.id LEFT JOIN analyses a ON a.video_id=v.id
              WHERE ch.creator_id=?""", (creator_id,)).fetchone()
        return dict(row)

    def export(self, creator_id):
        with self.connection() as connection:
            result = {}
            result["creator"] = [dict(row) for row in connection.execute("SELECT * FROM creators WHERE id=?", (creator_id,))]
            result["channels"] = [dict(row) for row in connection.execute("SELECT * FROM channels WHERE creator_id=? ORDER BY id", (creator_id,))]
            result["videos"] = [dict(row) for row in connection.execute("SELECT v.* FROM videos v JOIN channels c ON c.id=v.channel_id WHERE c.creator_id=? ORDER BY v.id", (creator_id,))]
            result["analyses"] = [dict(row) for row in connection.execute("SELECT a.* FROM analyses a JOIN videos v ON v.id=a.video_id JOIN channels c ON c.id=v.channel_id WHERE c.creator_id=? ORDER BY a.id", (creator_id,))]
            result["experiments"] = [dict(row) for row in connection.execute("SELECT e.* FROM experiments e JOIN videos v ON v.id=e.video_id JOIN channels c ON c.id=v.channel_id WHERE c.creator_id=? ORDER BY e.id", (creator_id,))]
        return result
