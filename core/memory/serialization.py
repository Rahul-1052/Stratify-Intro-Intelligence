"""Stable adapter from an existing completed report to memory fields."""

import hashlib
import json
import re
from urllib.parse import parse_qs, urlparse

UNKNOWN = {None, "", "unknown", "unavailable", "uncertain", "not_yet_reviewed"}


def stable_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _known(value):
    return None if value in UNKNOWN else value


def youtube_video_id(url):
    parsed = urlparse(str(url or ""))
    host = parsed.netloc.lower().split(":")[0]
    if host in {"youtu.be", "www.youtu.be"}:
        return parsed.path.strip("/").split("/")[0] or None
    if host.endswith("youtube.com"):
        if parsed.path == "/watch":
            return (parse_qs(parsed.query).get("v") or [None])[0]
        match = re.match(r"^/(?:shorts|embed|live)/([^/?]+)", parsed.path)
        return match.group(1) if match else None
    return None


def source_identity(source_url="", upload_name="", content_digest=None):
    external = youtube_video_id(source_url)
    if external:
        return {"external_video_id": external, "source_fingerprint": None, "decision": "matched_external_video_id"}
    material = content_digest or f"{str(upload_name).strip().lower()}|{str(source_url).strip()}"
    fingerprint = hashlib.sha256(material.encode("utf-8")).hexdigest() if material.strip("|") else None
    return {"external_video_id": None, "source_fingerprint": fingerprint, "decision": "matched_source_fingerprint" if fingerprint else "new_project_without_identifier"}


def normalize_report(report, analysis_version=None):
    report = _mapping(report)
    creator = _mapping(report.get("creator_report"))
    structure = _mapping(report.get("creative_structure"))
    understanding = _mapping(report.get("creative_understanding"))
    semantic = _mapping(report.get("semantic_observation"))
    confidence = _mapping(creator.get("confidence_summary"))
    opportunity = _mapping(creator.get("biggest_opportunity"))
    experiments = creator.get("experiments") if isinstance(creator.get("experiments"), list) else []
    text_confidence = confidence.get("text_evidence") or semantic.get("text_evidence_confidence")
    written_state = "limited" if text_confidence == "limited" else _known(semantic.get("information_mode") or semantic.get("text_role"))
    subject_pattern = _known(semantic.get("subject_presence_pattern"))
    multiple = None
    if subject_pattern:
        multiple = subject_pattern == "multiple_subjects"
    limitations = list(report.get("warnings") or [])
    if opportunity.get("limitation"):
        limitations.append(str(opportunity["limitation"]))
    return {
        "analysis_version": str(analysis_version or report.get("analysis_version") or creator.get("report_version") or "unknown"),
        "snapshot": _mapping(creator.get("opening_snapshot")),
        "creative_structure": structure,
        "creative_understanding": understanding,
        "reasoning_summary": {
            "status": creator.get("creative_reasoning_status"),
            "additional_observations": creator.get("additional_observations") or [],
        },
        "opportunity": opportunity,
        "experiments": experiments,
        "confidence_summary": confidence,
        "evidence_limitations": sorted(set(filter(None, map(str, limitations)))),
        "analysis_completeness": str(confidence.get("analysis_completeness") or report.get("status") or "limited"),
        "opening_strategy": _known(structure.get("opening_strategy")),
        "primary_visual_focus": _known(semantic.get("primary_visual_focus")),
        "progression_style": _known(structure.get("structural_rhythm") or semantic.get("visual_progression")),
        "subject_timing": _known(structure.get("reveal_pattern")),
        "subject_presence": subject_pattern,
        "multiple_subjects": multiple,
        "written_information_state": written_state,
        "recommendation_state": "supported" if opportunity.get("supported") else "abstained",
        "recommendation_confidence": _known(confidence.get("recommendation_confidence")),
    }
