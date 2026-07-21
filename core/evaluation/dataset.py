"""JSON-backed evaluation dataset loading and history persistence."""

import json
from pathlib import Path

from core.evaluation.evaluation_models import EvaluationVideo


class EvaluationDatasetStore:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return {"name": self.path.stem or "evaluation", "videos": []}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        videos = [EvaluationVideo.from_dict(item) for item in payload.get("videos", [])]
        return {"name": payload.get("name") or self.path.stem, "videos": videos}

    def save(self, name, videos):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"name": name, "videos": [item.to_dict() if isinstance(item, EvaluationVideo) else item for item in videos]}
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return self.path

    def append_history(self, video_id, history_item):
        dataset = self.load()
        for video in dataset["videos"]:
            if video.video_id == video_id:
                video.evaluation_history.append(dict(history_item))
                video.status = history_item.get("status", video.status)
                break
        self.save(dataset["name"], dataset["videos"])
