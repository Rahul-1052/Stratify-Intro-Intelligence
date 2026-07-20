"""Minimal local project state suitable for Streamlit session storage."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Mapping
from uuid import uuid4


@dataclass
class CreativeProject:
    project_id: str
    title: str
    source_type: str
    source_url: str = ""
    upload_name: str = ""
    created_at: str = ""
    active_module: str = "intro_intelligence"
    module_run_statuses: Dict[str, str] = field(default_factory=dict)
    module_results: Dict[str, Any] = field(default_factory=dict)
    experiments: list = field(default_factory=list)

    def to_session(self):
        return asdict(self)

    def record_result(self, module_id, result):
        self.module_results[module_id] = result
        self.module_run_statuses[module_id] = str((result or {}).get("status", "complete"))
        if module_id == "intro_intelligence":
            self.experiments = list(((result or {}).get("creator_report") or {}).get("experiments", []))


def create_project(source_url="", upload_name="", title="Untitled video project"):
    source_type = "youtube_url" if source_url else "video_upload" if upload_name else "local_project"
    return CreativeProject(
        project_id=uuid4().hex,
        title=title.strip() or "Untitled video project",
        source_type=source_type,
        source_url=source_url.strip(),
        upload_name=upload_name,
        created_at=datetime.now(timezone.utc).isoformat(),
        module_run_statuses={"intro_intelligence": "ready"},
    )


def restore_project(value):
    if isinstance(value, CreativeProject):
        return value
    if not isinstance(value, Mapping):
        return None
    allowed = CreativeProject.__dataclass_fields__
    return CreativeProject(**{key: item for key, item in value.items() if key in allowed})
