"""JSON-backed evaluation dataset loading and history persistence."""

import json
from pathlib import Path

from core.evaluation.evaluation_models import EvaluationVideo


class EvaluationDatasetStore:
    def __init__(self, path):
        self.path = Path(path)
        self._top_level_extra = {}

    def load(self):
        if not self.path.exists():
            return {"name": self.path.stem or "evaluation", "videos": []}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self._top_level_extra = {key: value for key, value in payload.items() if key not in {"name", "videos"}}
        videos = [EvaluationVideo.from_dict(item) for item in payload.get("videos", [])]
        return {"name": payload.get("name") or self.path.stem, "videos": videos, **self._top_level_extra}

    def save(self, name, videos):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {**self._top_level_extra, "name": name, "videos": [item.to_dict() if isinstance(item, EvaluationVideo) else item for item in videos]}
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return self.path

    def append_history(self, video_id, history_item):
        dataset = self.load()
        for video in dataset["videos"]:
            if video.video_id == video_id:
                video.evaluation_history.append(dict(history_item))
                if history_item.get("review_status"):
                    video.status = history_item["review_status"]
                break
        self.save(dataset["name"], dataset["videos"])

    def save_manual_review(self, evaluation_id, labels, review_status, reviewer_notes=""):
        from core.evaluation.dataset_validation import validate_dataset

        dataset = self.load()
        matched = False
        for video in dataset["videos"]:
            if (video.evaluation_id or video.video_id) == evaluation_id:
                video.expected_manual_labels = dict(labels or {})
                video.status = review_status
                video.reviewer_notes = reviewer_notes or None
                matched = True
                break
        if not matched:
            raise KeyError(f"Unknown evaluation entry: {evaluation_id}")
        errors = validate_dataset(dataset, require_v1_shape=False)
        if errors:
            raise ValueError("; ".join(errors))
        self.save(dataset["name"], dataset["videos"])
        return next(video for video in dataset["videos"] if (video.evaluation_id or video.video_id) == evaluation_id)
