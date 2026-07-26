"""Atomic repository-local storage, isolated from Creator Memory."""

import json
import os
from pathlib import Path


class ValidationStore:
    def __init__(self, root=".stratify_validation"):
        self.root = Path(root)
        for name in ("runs", "reports", "reviews", "exports"):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def _write(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        os.replace(temporary, path)
        return path

    def save_run(self, run):
        payload = run.to_dict() if hasattr(run, "to_dict") else run
        return self._write(self.root / "runs" / f"{payload['run_id']}.json", payload)

    def load_run(self, run_id):
        return json.loads((self.root / "runs" / f"{run_id}.json").read_text(encoding="utf-8"))

    def list_runs(self):
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted((self.root / "runs").glob("*.json"), reverse=True)]

    def save_report(self, run_id, case_id, report):
        return self._write(self.root / "reports" / run_id / f"{case_id}.json", report)

    def load_report(self, reference):
        return json.loads((self.root / reference).read_text(encoding="utf-8"))

    def save_review(self, run_id, case_id, review):
        if not str(review.get("one_change", "")).strip():
            raise ValueError("The one-change field is required.")
        path = self._write(self.root / "reviews" / run_id / f"{case_id}.json", review)
        run = self.load_run(run_id)
        matched = False
        for case in run.get("cases", []):
            if case.get("case_id") == case_id:
                case.update(review)
                matched = True
                break
        if not matched:
            raise KeyError(f"Unknown validation case: {case_id}")
        self.save_run(run)
        return path
