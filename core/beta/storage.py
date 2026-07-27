"""Versioned local persistence for private-beta operational data."""

import csv
import json
import os
import tempfile
from pathlib import Path


SCHEMA_VERSION = 1


class BetaStore:
    COLLECTIONS = ("analytics", "feedback", "testers", "reviews", "exports")

    def __init__(self, root=".stratify_beta"):
        self.root = Path(root)
        for name in self.COLLECTIONS:
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def _path(self, collection, record_id):
        if collection not in self.COLLECTIONS:
            raise ValueError(f"Unknown beta collection: {collection}")
        safe_id = "".join(c for c in str(record_id) if c.isalnum() or c in "-_")
        if not safe_id:
            raise ValueError("A record ID is required.")
        return self.root / collection / f"{safe_id}.json"

    def save(self, collection, record_id, payload):
        value = dict(payload)
        value.setdefault("schema_version", SCHEMA_VERSION)
        destination = self._path(collection, record_id)
        fd, temporary = tempfile.mkstemp(
            prefix=f".{destination.stem}-", suffix=".tmp", dir=destination.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return destination

    def load(self, collection, record_id):
        path = self._path(collection, record_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        return self._migrate(payload)

    def list(self, collection):
        folder = self.root / collection
        records = []
        for path in sorted(folder.glob("*.json")):
            value = self.load(collection, path.stem)
            if value is not None:
                records.append(value)
        return records

    @staticmethod
    def _migrate(payload):
        value = dict(payload)
        version = int(value.get("schema_version") or 0)
        if version == 0:
            value["schema_version"] = SCHEMA_VERSION
        return value

    def export_csv(self, collection, destination=None):
        records = self.list(collection)
        destination = Path(destination or self.root / "exports" / f"{collection}.csv")
        destination.parent.mkdir(parents=True, exist_ok=True)
        flat = [_flatten(record) for record in records]
        fields = sorted({key for record in flat for key in record})
        with destination.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields or ["schema_version"])
            writer.writeheader()
            writer.writerows(flat)
        return destination


def _flatten(value, prefix=""):
    output = {}
    for key, item in value.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            output.update(_flatten(item, name))
        elif isinstance(item, list):
            output[name] = json.dumps(item, ensure_ascii=False, sort_keys=True)
        else:
            output[name] = item
    return output
