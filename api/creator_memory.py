"""Web-safe adapter over recovered Creator Memory; keeps persistence semantics in Python."""
from dataclasses import asdict, is_dataclass
from pathlib import Path

from core.memory.service import CreatorMemoryService
from stratify_platform.projects import create_project


def _jsonable(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def memory_service(database_path: str | Path | None = None):
    return CreatorMemoryService(database_path)


def save_uploaded_analysis(report, upload_name: str, content_digest: str, database_path=None):
    service = memory_service(database_path)
    project = create_project(upload_name=upload_name or "owned-video.mp4", title=upload_name or "Owned video")
    saved = service.save_report(report, project, content_digest=content_digest)
    return {**saved, "dashboard": _jsonable(service.dashboard())}


def reopen_analysis(analysis_id: str, database_path=None):
    return _jsonable(memory_service(database_path).reopen_analysis(analysis_id))


def dashboard(database_path=None):
    return _jsonable(memory_service(database_path).dashboard())


def save_profile(display_name: str, channel_name: str, niche: str | None = None, database_path=None):
    profile = memory_service(database_path).save_profile(display_name, channel_name, niche=niche)
    return _jsonable(profile)


def update_experiment(experiment_id: str, status: str | None = None, creator_notes: str | None = None,
                      result_summary: str | None = None, database_path=None):
    service = memory_service(database_path)
    updates = {}
    if status is not None:
        updates["status"] = status
    if creator_notes is not None:
        updates["creator_notes"] = creator_notes
    if result_summary is not None:
        updates["result_summary"] = result_summary
    service.update_experiment(experiment_id, **updates)
    return _jsonable(service.dashboard())
