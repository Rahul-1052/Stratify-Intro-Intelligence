"""Private-beta feedback, analytics, scorecards, testers, and summaries."""

import csv
import hashlib
import json
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .storage import BetaStore, SCHEMA_VERSION


REVIEW_FIELDS = (
    "strongest_insight_usefulness", "evidence_specificity",
    "experiment_actionability", "trustworthiness", "clarity", "novelty",
)
BOOL_REVIEW_FIELDS = (
    "generic_language_present", "recommendation_sensible",
    "contradiction_present", "report_worth_revisiting",
)
FORBIDDEN_ANALYTICS_FIELDS = {
    "raw_video", "video_contents", "frames", "full_report", "report_prose",
    "name", "email", "ip", "ip_address", "device_fingerprint", "user_agent",
}
ALLOWED_EVENTS = {
    "analysis_started", "analysis_completed", "analysis_failed", "report_viewed",
    "timeline_viewed", "strongest_finding_viewed", "primary_experiment_viewed",
    "evidence_section_expanded", "benchmark_panel_viewed", "builder_mode_opened",
    "feedback_submitted", "another_analysis_started",
}
THEMES = {
    "unclear wording": ("confusing", "unclear", "wording", "understand"),
    "generic advice": ("generic", "vague", "obvious"),
    "experiment timing": ("timing", "timestamp", "when", "seconds"),
    "evidence trust": ("evidence", "trust", "proof", "believe"),
    "benchmark confusion": ("benchmark", "median", "comparison"),
    "report length": ("long", "shorter", "length", "too much"),
    "UI navigation": ("navigation", "find", "expand", "scroll"),
    "missing feature": ("missing", "wish", "feature", "need"),
    "performance": ("slow", "speed", "performance", "loading"),
    "upload problem": ("upload", "file", "video failed"),
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def report_identifier(report):
    video = report.get("video") or {}
    source = (
        video.get("video_id") or report.get("report_id")
        or (report.get("source_context") or {}).get("source_id")
        or report.get("url") or "local-report"
    )
    return hashlib.sha256(str(source).encode("utf-8")).hexdigest()[:16]


def extract_feedback_themes(records):
    counts = Counter()
    for record in records:
        answers = record.get("answers") or {}
        text = " ".join(
            str(answers.get(key) or "")
            for key in ("confusing", "free_text")
        ).lower()
        for theme, keywords in THEMES.items():
            if any(keyword in text for keyword in keywords):
                counts[theme] += 1
    return [{"theme": name, "count": counts[name]} for name in sorted(counts)]


def _metadata_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key).lower()
            yield from _metadata_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _metadata_keys(item)


class BetaService:
    def __init__(self, store=None):
        self.store = store or BetaStore()

    def submit_feedback(self, report_id, source_type, recommendation_state, answers,
                        session_id="", submission_key=""):
        duplicate_key = submission_key or f"{session_id}:{report_id}"
        duplicate_id = hashlib.sha256(duplicate_key.encode("utf-8")).hexdigest()[:20]
        if duplicate_key and self.store.load("feedback", duplicate_id):
            return {"status": "duplicate", "feedback_id": duplicate_id}
        payload = {
            "feedback_id": duplicate_id or uuid.uuid4().hex,
            "report_id": report_id,
            "timestamp": now_iso(),
            "source_type": source_type or "unknown",
            "recommendation_state": recommendation_state or "unknown",
            "answers": dict(answers),
            "schema_version": SCHEMA_VERSION,
        }
        self.store.save("feedback", payload["feedback_id"], payload)
        return {"status": "saved", **payload}

    def track(self, event_name, session_id, report_id="", source_type="unknown",
              metadata=None):
        if event_name not in ALLOWED_EVENTS:
            raise ValueError(f"Unsupported analytics event: {event_name}")
        metadata = dict(metadata or {})
        forbidden = FORBIDDEN_ANALYTICS_FIELDS.intersection(_metadata_keys(metadata))
        if forbidden:
            raise ValueError("Analytics metadata contains a prohibited privacy field.")
        payload = {
            "event_id": uuid.uuid4().hex,
            "session_id": session_id,
            "report_id": report_id,
            "event_name": event_name,
            "timestamp": now_iso(),
            "source_type": source_type,
            "metadata": metadata,
            "schema_version": SCHEMA_VERSION,
        }
        self.store.save("analytics", payload["event_id"], payload)
        return payload

    def safe_track(self, *args, **kwargs):
        try:
            return self.track(*args, **kwargs)
        except Exception:
            return None

    def save_review(self, case_id, reviewer_id, values):
        missing = [
            key for key in (*REVIEW_FIELDS, *BOOL_REVIEW_FIELDS)
            if values.get(key) in {None, ""}
        ]
        completed = not missing
        for key in REVIEW_FIELDS:
            if values.get(key) not in {None, ""} and int(values[key]) not in range(1, 6):
                raise ValueError(f"{key} must be between 1 and 5.")
        review_id = hashlib.sha256(
            f"{case_id}:{reviewer_id}".encode("utf-8")
        ).hexdigest()[:20]
        payload = {
            "review_id": review_id, "case_id": case_id,
            "reviewer_id": reviewer_id, "timestamp": now_iso(),
            "completed": completed, "missing_fields": missing,
            "scores": {key: values.get(key) for key in REVIEW_FIELDS},
            "checks": {key: values.get(key) for key in BOOL_REVIEW_FIELDS},
            "reviewer_notes": values.get("reviewer_notes", ""),
            "schema_version": SCHEMA_VERSION,
        }
        self.store.save("reviews", review_id, payload)
        return payload

    def upsert_tester(self, tester):
        tester_id = str(tester.get("tester_id") or "").strip()
        if not tester_id:
            raise ValueError("tester_id is required.")
        existing = self.store.load("testers", tester_id) or {}
        payload = {
            "tester_id": tester_id,
            "display_name": tester.get("display_name", existing.get("display_name", "")),
            "contact": tester.get("contact", existing.get("contact", "")),
            "invite_status": tester.get("invite_status", existing.get("invite_status", "planned")),
            "invited_date": tester.get("invited_date", existing.get("invited_date", "")),
            "first_use_date": tester.get("first_use_date", existing.get("first_use_date", "")),
            "latest_use_date": tester.get("latest_use_date", existing.get("latest_use_date", "")),
            "reports_generated": int(tester.get("reports_generated", existing.get("reports_generated", 0))),
            "feedback_submitted": int(tester.get("feedback_submitted", existing.get("feedback_submitted", 0))),
            "follow_up_status": tester.get("follow_up_status", existing.get("follow_up_status", "")),
            "notes": tester.get("notes", existing.get("notes", "")),
            "schema_version": SCHEMA_VERSION,
        }
        self.store.save("testers", tester_id, payload)
        return payload

    def import_testers_csv(self, path):
        with Path(path).open(encoding="utf-8-sig", newline="") as handle:
            return [self.upsert_tester(row) for row in csv.DictReader(handle)]

    def dashboard_summary(self, golden_summary=None):
        events = self.store.list("analytics")
        feedback = self.store.list("feedback")
        reviews = [item for item in self.store.list("reviews") if item.get("completed")]
        event_counts = Counter(item.get("event_name") for item in events)
        sessions = Counter(
            item.get("session_id") for item in events
            if item.get("event_name") == "analysis_completed"
        )
        usefulness = [
            int((item.get("answers") or {}).get("usefulness"))
            for item in feedback
            if str((item.get("answers") or {}).get("usefulness", "")).isdigit()
        ]
        useful_sections = Counter(
            (item.get("answers") or {}).get("most_useful_section")
            for item in feedback if (item.get("answers") or {}).get("most_useful_section")
        )
        def yes_percent(field):
            answers = [
                (item.get("answers") or {}).get(field) for item in feedback
                if (item.get("answers") or {}).get(field) is not None
            ]
            return round(100 * sum(value is True or str(value).lower() == "yes" for value in answers) / len(answers), 1) if answers else None
        review_averages = {
            key: round(sum(int(item["scores"][key]) for item in reviews) / len(reviews), 2)
            for key in REVIEW_FIELDS if reviews
        }
        return {
            "total_reports_generated": event_counts["analysis_completed"],
            "completed_analyses": event_counts["analysis_completed"],
            "failed_analyses": event_counts["analysis_failed"],
            "repeat_analyses_by_session": sum(count - 1 for count in sessions.values() if count > 1),
            "feedback_count": len(feedback),
            "average_usefulness": round(sum(usefulness) / len(usefulness), 2) if usefulness else None,
            "experiment_intent_percentage": yes_percent("try_experiment"),
            "next_upload_reuse_intent": yes_percent("use_before_next_upload"),
            "willingness_to_pay_count": sum(
                (item.get("answers") or {}).get("would_pay") is True
                or str((item.get("answers") or {}).get("would_pay", "")).lower() == "yes"
                for item in feedback
            ),
            "most_useful_sections": dict(useful_sections),
            "confusion_themes": extract_feedback_themes(feedback),
            "unresolved_validation_warnings": sum(
                int((item.get("metadata") or {}).get("validation_warning_count", 0))
                for item in events if item.get("event_name") == "analysis_completed"
            ),
            "review_averages": review_averages,
            "review_sample_size": len(reviews),
            "feedback_sample_size": len(feedback),
            "golden_dataset": golden_summary or {},
        }

    def export_review_summary_markdown(self, summary, destination=None):
        destination = Path(
            destination or self.store.root / "exports" / "beta_review_summary.md"
        )
        lines = [
            "# Stratify Private Beta Review",
            "",
            f"- Reports generated: {summary['total_reports_generated']}",
            f"- Feedback responses: {summary['feedback_count']} (n={summary['feedback_sample_size']})",
            f"- Completed human reviews: {summary['review_sample_size']}",
            "- Small samples are directional operational feedback, not statistically significant.",
        ]
        destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return destination

    def export_analytics_summary_csv(self, summary=None, destination=None):
        summary = summary or self.dashboard_summary()
        destination = Path(
            destination or self.store.root / "exports" / "analytics_summary.csv"
        )
        rows = [
            ("total_reports_generated", summary["total_reports_generated"]),
            ("completed_analyses", summary["completed_analyses"]),
            ("failed_analyses", summary["failed_analyses"]),
            ("repeat_analyses_by_session", summary["repeat_analyses_by_session"]),
            ("feedback_count", summary["feedback_count"]),
        ]
        with destination.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(("metric", "value"))
            writer.writerows(rows)
        return destination
