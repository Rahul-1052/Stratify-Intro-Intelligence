"""Small versioned JSON cache for free benchmark search evidence."""

import hashlib
import json
import os
import time
from pathlib import Path

CACHE_VERSION = "benchmark-search-v2"
DEFAULT_TTL_SECONDS = 24 * 60 * 60


def cache_path():
    configured = os.getenv("STRATIFY_BENCHMARK_CACHE")
    return Path(configured) if configured else Path(".stratify_cache") / "benchmark_search_v2.json"


def make_key(query, max_results, order="relevance"):
    normalized = " ".join(str(query or "").lower().split())
    payload = f"{CACHE_VERSION}|{normalized}|{int(max_results)}|{order}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read(query, max_results, order="relevance", ttl_seconds=DEFAULT_TTL_SECONDS, now=None):
    path = cache_path()
    if not path.exists():
        return None, {"status": "miss", "cached_evidence_used": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entry = data.get("entries", {}).get(make_key(query, max_results, order))
        if not entry or data.get("version") != CACHE_VERSION:
            return None, {"status": "miss", "cached_evidence_used": False}
        age = float(now if now is not None else time.time()) - float(entry.get("created_at", 0))
        if age > ttl_seconds:
            return None, {"status": "expired", "cached_evidence_used": False, "age_seconds": round(age, 1)}
        return list(entry.get("results", [])), {"status": "hit", "cached_evidence_used": True, "age_seconds": round(age, 1)}
    except (OSError, ValueError, TypeError):
        return None, {"status": "invalid", "cached_evidence_used": False}


def write(query, max_results, results, order="relevance", now=None):
    path = cache_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        data = {}
    if data.get("version") != CACHE_VERSION:
        data = {"version": CACHE_VERSION, "entries": {}}
    data.setdefault("entries", {})[make_key(query, max_results, order)] = {
        "created_at": float(now if now is not None else time.time()), "results": list(results or [])
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temporary.replace(path)

