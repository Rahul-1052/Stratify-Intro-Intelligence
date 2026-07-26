"""Truthful typed source resolution before shared media intelligence."""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List

import cv2

SOURCE_TYPES = {"youtube_url", "uploaded_file", "cached_local_clip"}


@dataclass
class SourceContext:
    source_type: str
    source_url: str = ""
    video_id: str = ""
    local_path: str = ""
    title: str = ""
    creator_or_channel: str = ""
    duration_seconds: float = 0.0
    metadata_status: str = "unavailable"
    acquisition_status: str = "pending"
    benchmark_context_status: str = "unavailable"
    provenance: str = ""
    warnings: List[str] = field(default_factory=list)

    def validate(self):
        if self.source_type not in SOURCE_TYPES:
            raise ValueError(f"Unsupported source type: {self.source_type}")
        if self.source_type == "youtube_url" and not self.source_url:
            raise ValueError("A YouTube source requires a URL.")
        if self.source_type != "youtube_url" and not self.local_path:
            raise ValueError("A local source requires a local path.")
        return self

    def to_dict(self):
        return asdict(self)

    def video_metadata(self):
        return {
            "video_id": self.video_id,
            "title": self.title,
            "description": "",
            "channel_title": self.creator_or_channel,
            "channel_id": "",
            "duration": self.duration_seconds,
            "views": None,
            "likes": None,
            "comments": None,
            "source_type": self.source_type,
            "metadata_status": self.metadata_status,
        }


def resolve_source_context(url="", local_path="", local_source_type="uploaded_file"):
    if local_path:
        source_type = local_source_type if local_source_type in {"uploaded_file", "cached_local_clip"} else "uploaded_file"
        path = Path(local_path)
        warnings = []
        readable = path.is_file()
        duration = _duration(path) if readable else 0.0
        if not readable:
            warnings.append("The local video file is unavailable.")
        elif not duration:
            warnings.append("The local video duration could not be read.")
        return SourceContext(
            source_type=source_type, local_path=str(path), duration_seconds=duration,
            metadata_status="unavailable", acquisition_status="available" if readable else "failed",
            benchmark_context_status="unavailable",
            provenance="user upload" if source_type == "uploaded_file" else "existing cached local clip",
            warnings=warnings + [
                "Creator, title, URL, channel statistics, and benchmark context are unavailable for this local source."
            ],
        ).validate()
    from core.youtube_client import extract_video_id
    return SourceContext(
        source_type="youtube_url", source_url=str(url or ""),
        video_id=extract_video_id(url) or "", metadata_status="pending",
        acquisition_status="pending", benchmark_context_status="pending",
        provenance="YouTube API and acquisition pipeline",
    ).validate()


def _duration(path):
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return 0.0
    frames = float(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    capture.release()
    return round(frames / fps, 3) if fps > 0 else 0.0
