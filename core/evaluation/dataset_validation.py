"""Validation and readiness for the manually reviewed V1 dataset."""

from collections import Counter


V1_CATEGORIES = (
    "cinematic_scene", "trailer", "educational_tutorial", "gaming", "interview_podcast",
)
REVIEW_STATES = {"unreviewed", "incomplete", "partial", "complete"}
UNSURE_VALUES = {"unavailable", "uncertain", "not_yet_reviewed"}
CONTROLLED_LABELS = {
    "primary_visual_focus": {"person", "multiple_people", "alternating_subjects", "object", "environment", "text", "mixed", "unavailable", "uncertain", "not_yet_reviewed"},
    "focus_clarity": {"immediate", "develops_early", "delayed", "competing", "unavailable", "uncertain", "not_yet_reviewed"},
    "opening_mode": {"subject_first", "text_first", "environment_first", "action_or_change_first", "mixed", "unavailable", "uncertain", "not_yet_reviewed"},
    "visual_progression": {"mostly_held", "gradual_change", "frequent_change", "distinct_beats", "unavailable", "uncertain", "not_yet_reviewed"},
    "text_role": {"absent", "supportive", "dominant", "persistent", "intermittent", "unavailable", "uncertain", "not_yet_reviewed"},
    "manual_confidence": {"high", "moderate", "limited", "unavailable", "uncertain", "not_yet_reviewed"},
}
REQUIRED_COMPLETE_FIELDS = (
    "primary_visual_focus", "focus_clarity", "opening_mode", "visual_progression",
    "text_role", "number_of_semantic_beats", "best_strength",
    "largest_weakness", "expected_experiment", "manual_confidence",
)


def _entry_dict(video):
    return video.to_dict() if hasattr(video, "to_dict") else dict(video)


def validate_dataset(dataset, require_v1_shape=True):
    videos = list(dataset.get("videos", []) or [])
    active = [video for video in videos if _entry_dict(video).get("active", True)]
    errors = []
    if require_v1_shape and len(active) != 15:
        errors.append(f"Dataset V1 requires exactly 15 active entries; found {len(active)}.")
    category_counts = Counter(video.category for video in active)
    if require_v1_shape:
        for category in V1_CATEGORIES:
            if category_counts.get(category, 0) != 3:
                errors.append(f"Category '{category}' requires 3 active entries; found {category_counts.get(category, 0)}.")
        unknown = sorted(set(category_counts) - set(V1_CATEGORIES))
        if unknown:
            errors.append("Unknown evaluation categories: " + ", ".join(unknown))
    evaluation_ids = [(video.evaluation_id or "").strip() for video in active]
    if any(not value for value in evaluation_ids):
        errors.append("Every active entry requires a stable evaluation_id.")
    duplicates = sorted(value for value, count in Counter(evaluation_ids).items() if value and count > 1)
    if duplicates:
        errors.append("Duplicate evaluation IDs: " + ", ".join(duplicates))
    video_ids = [video.video_id for video in active]
    duplicate_videos = sorted(value for value, count in Counter(video_ids).items() if value and count > 1)
    if duplicate_videos:
        errors.append("Duplicate video IDs require explicit documentation: " + ", ".join(duplicate_videos))
    for video in active:
        identity = video.evaluation_id or video.video_id
        if video.status not in REVIEW_STATES:
            errors.append(f"{identity}: invalid review status '{video.status}'.")
        labels = video.expected_manual_labels or {}
        for field, allowed in CONTROLLED_LABELS.items():
            if field in labels and labels[field] not in allowed:
                errors.append(f"{identity}: invalid {field} label '{labels[field]}'.")
        beat_count = labels.get("number_of_semantic_beats")
        if beat_count is not None and not (isinstance(beat_count, int) and beat_count >= 0) and beat_count not in UNSURE_VALUES:
            errors.append(f"{identity}: number_of_semantic_beats must be a non-negative integer or an uncertainty value.")
        experiment = labels.get("expected_experiment")
        if experiment is not None and not isinstance(experiment, (str, list)):
            errors.append(f"{identity}: expected_experiment must be text or a list of text values.")
        if isinstance(experiment, list) and not all(isinstance(item, str) for item in experiment):
            errors.append(f"{identity}: expected_experiment list values must be text.")
        if video.status == "complete":
            missing = [
                field for field in REQUIRED_COMPLETE_FIELDS
                if field not in labels
                or labels[field] is None
                or labels[field] == ""
                or labels[field] == "not_yet_reviewed"
            ]
            if missing:
                errors.append(f"{identity}: completed review is missing required fields: {', '.join(missing)}.")
    return errors


def dataset_readiness(dataset):
    videos = [video for video in dataset.get("videos", []) or [] if _entry_dict(video).get("active", True)]
    counts = Counter(video.status for video in videos)
    total = len(videos)
    complete = counts.get("complete", 0)
    errors = validate_dataset(dataset, require_v1_shape=True)
    return {
        "total_entries": total,
        "unreviewed_entries": counts.get("unreviewed", 0),
        "incomplete_entries": counts.get("incomplete", 0),
        "partially_reviewed_entries": counts.get("partial", 0),
        "completed_entries": complete,
        "completion_percentage": round(100 * complete / total, 1) if total else 0.0,
        "category_balance": dict(sorted(Counter(video.category for video in videos).items())),
        "baseline_v1_ready": total == 15 and complete == total and not errors,
        "validation_errors": errors,
    }
