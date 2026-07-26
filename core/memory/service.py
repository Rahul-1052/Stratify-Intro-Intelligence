import json
import os
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from core.memory.aggregator import aggregate
from core.memory.comparison import compare_current
from core.memory.models import AnalysisRecord, Channel, Creator, Experiment, VideoProject
from core.memory.repository import MemoryRepository
from core.memory.reconstruction import reconstruct_creator_report
from core.memory.schema import SCHEMA_VERSION
from core.memory.serialization import normalize_report, source_identity, stable_json

DEFAULT_DATABASE_PATH = Path(".stratify_data") / "creator_memory.db"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class CreatorMemoryService:
    def __init__(self, database_path=None, now=utc_now):
        self.database_path = Path(database_path or os.getenv("STRATIFY_MEMORY_DB", DEFAULT_DATABASE_PATH))
        self.now = now
        self.repository = MemoryRepository(self.database_path, now)
        self.diagnostics = {"database_path": str(self.database_path), "schema_version": SCHEMA_VERSION}

    def profile(self):
        return self.repository.primary_profile()

    def save_profile(self, display_name, channel_name, channel_url=None, external_channel_id=None,
                     niche=None, platform="youtube", creator_id=None, channel_id=None, notes=""):
        current = self.profile()
        timestamp = self.now()
        creator_id = creator_id or (current or {}).get("id") or uuid4().hex
        channel_id = channel_id or (current or {}).get("channel_id") or uuid4().hex
        created = (current or {}).get("created_at") or timestamp
        self.repository.save_creator(Creator(creator_id, display_name.strip(), created, timestamp, notes))
        self.repository.save_channel(Channel(
            channel_id, creator_id, platform, channel_name.strip(), (current or {}).get("channel_created_at") or timestamp,
            timestamp, external_channel_id or None, channel_url or None, niche or None,
        ))
        self.diagnostics.update({"selected_creator_id": creator_id, "selected_channel_id": channel_id})
        return self.profile()

    def prepare(self, report):
        return normalize_report(report)

    def comparison(self, report, creator_id=None):
        profile = self.profile()
        if not (creator_id or profile):
            return {"state": "insufficient_history", "message": "Create a local profile to compare this opening with saved history.", "evidence": {}}
        normalized = normalize_report(report)
        records, errors = self.repository.analyses_for_creator(creator_id or profile["id"])
        result = compare_current(normalized, records)
        self.diagnostics.update({"normalization_output": normalized, "comparison_evidence": result["evidence"], "corrupt_records": errors})
        return result

    def save_report(self, report, project, content_digest=None):
        profile = self.profile()
        if not profile:
            raise ValueError("Create a Creator Memory profile before saving.")
        timestamp = self.now()
        identity = source_identity(project.source_url, project.upload_name, content_digest)
        video = VideoProject(
            id=uuid4().hex, channel_id=profile["channel_id"], source_type=project.source_type,
            analysis_status=str(report.get("status") or "complete"), created_at=timestamp, analyzed_at=timestamp,
            external_video_id=identity["external_video_id"], source_url=project.source_url or None,
            title=(report.get("video") or {}).get("title") or project.title or None,
            source_fingerprint=identity["source_fingerprint"],
        )
        video_id, decision = self.repository.resolve_video(video)
        normalized = normalize_report(report)
        analysis_id = uuid4().hex
        normalized.update({"id": analysis_id, "video_id": video_id, "created_at": timestamp})
        analysis = AnalysisRecord(**{
            field.name: normalized.get(field.name) for field in fields(AnalysisRecord)
        })
        experiments = []
        for item in analysis.experiments:
            experiments.append(Experiment(
                id=uuid4().hex, analysis_id=analysis_id, video_id=video_id,
                dimension=str(item.get("structural_dimension") or item.get("dimension") or "unspecified"),
                hypothesis=str(item.get("hypothesis") or ""), change_description=str(item.get("change") or item.get("recommendation") or ""),
                keep_constant=str(item.get("what_stays_constant") or ""), version_a=str(item.get("version_a") or ""),
                version_b=str(item.get("version_b") or ""), confidence=str(item.get("confidence") or "limited"),
                limitation=str(item.get("limitation") or ""), status="suggested", created_at=timestamp, updated_at=timestamp,
            ))
        self.repository.save_analysis_with_experiments(analysis, experiments)
        self.diagnostics.update({
            "saved_analysis_id": analysis_id, "duplicate_resolution_decision": decision,
            "normalization_output": normalized,
        })
        return {"analysis_id": analysis_id, "video_id": video_id, "decision": decision}

    def dashboard(self, creator_id=None):
        profile = self.profile()
        creator_id = creator_id or (profile or {}).get("id")
        if not creator_id:
            return {"profile": None, "counts": {"videos": 0, "analyses": 0}, "memory": aggregate([]), "history": [], "experiments": [], "errors": []}
        analyses, errors = self.repository.analyses_for_creator(creator_id)
        experiments = self.repository.experiments_for_creator(creator_id)
        memory = aggregate(analyses, experiments)
        self.diagnostics.update({"aggregation_counts": memory["analyses_count"], "confidence_reasons": memory["confidence_reasons"], **memory["diagnostics"]})
        return {
            "profile": profile, "counts": self.repository.counts(creator_id), "memory": memory,
            "history": self.repository.history(creator_id), "experiments": experiments, "errors": errors,
        }

    def reopen_analysis(self, analysis_id):
        record, metadata = self.repository.analysis_for_reopen(analysis_id)
        if record is None:
            result = {
                "status": "fallback",
                "message": "This saved analysis could not be opened. The rest of your history is still available.",
                "unavailable_details": ["Some saved details are unreadable or no longer available."],
                "diagnostics": metadata,
            }
        else:
            result = reconstruct_creator_report(
                record, video=metadata, revision=metadata.get("revision") or 1
            )
        self.diagnostics["saved_report_reconstruction"] = result.get("diagnostics", {})
        return result

    def update_experiment(self, experiment_id, **updates):
        self.repository.update_experiment(experiment_id, **updates)

    def delete_project(self, video_id):
        self.repository.delete_project(video_id)

    def delete_analysis(self, analysis_id):
        self.repository.delete_analysis(analysis_id)

    def reset(self):
        profile = self.profile()
        if profile:
            self.repository.reset_creator(profile["id"])

    def export_json(self):
        profile = self.profile()
        if not profile:
            raise ValueError("There is no Creator Memory profile to export.")
        payload = {
            "schema_version": SCHEMA_VERSION, "exported_at": self.now(),
            **self.repository.export(profile["id"]),
        }
        return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False)

    @staticmethod
    def validate_export(value):
        payload = json.loads(value) if isinstance(value, str) else value
        required = {"schema_version","creator","channels","videos","analyses","experiments","exported_at"}
        if not isinstance(payload, dict) or not required.issubset(payload):
            raise ValueError("This is not a valid Creator Memory export.")
        if payload["schema_version"] > SCHEMA_VERSION:
            raise ValueError("This export uses a newer unsupported schema.")
        return True
