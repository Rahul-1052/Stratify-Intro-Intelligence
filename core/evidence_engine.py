def _as_dict(value):
    return value if isinstance(value, dict) else {}


def _as_list(value):
    return value if isinstance(value, list) else []


def _feature_summary(feature_report):
    return _as_dict(_as_dict(feature_report).get("feature_summary"))


def _benchmark_item_summary(item):
    item = _as_dict(item)
    video = _as_dict(item.get("video"))
    features = _as_dict(item.get("features"))
    return {
        "video_id": video.get("video_id", ""),
        "status": item.get("status", "unknown"),
        "feature_summary": _feature_summary(features),
        "vision": _as_dict(item.get("vision")),
        "stage": item.get("stage", ""),
        "error": item.get("error", ""),
    }


def _benchmark_summaries(items):
    return [_benchmark_item_summary(item) for item in _as_list(items)]


def _confidence(warnings, intro_summary, benchmark_features):
    top = _benchmark_summaries(_as_dict(benchmark_features).get("top_performers"))
    lower = _benchmark_summaries(_as_dict(benchmark_features).get("lower_performers"))
    top_success_count = sum(item.get("status") == "success" for item in top)
    lower_success_count = sum(item.get("status") == "success" for item in lower)
    return {
        "warnings": _as_list(warnings),
        "has_intro_visual_evidence": bool(intro_summary),
        "top_benchmark_intro_count": top_success_count,
        "lower_benchmark_intro_count": lower_success_count,
    }


def build_evidence(
    video=None,
    channel=None,
    recent_videos=None,
    intro_feature_report=None,
    intro_observation=None,
    benchmark=None,
    benchmark_features=None,
    category=None,
    transcript=None,
    context=None,
    warnings=None,
):
    intro_summary = _feature_summary(intro_feature_report)
    benchmark_features = _as_dict(benchmark_features)

    return {
        "video": {
            "metadata": _as_dict(video),
            "channel": _as_dict(channel),
            "recent_videos": _as_list(recent_videos),
        },
        "intro": {
            "feature_summary": intro_summary,
            "observation": _as_dict(intro_observation),
        },
        "benchmark": {
            "metadata": _as_dict(benchmark),
            "top_performers": _benchmark_summaries(
                benchmark_features.get("top_performers")
            ),
            "lower_performers": _benchmark_summaries(
                benchmark_features.get("lower_performers")
            ),
        },
        "context": {
            "category": _as_dict(category),
            "intelligence": _as_dict(context),
        },
        "transcript": _as_dict(transcript),
        "confidence": _confidence(warnings, intro_summary, benchmark_features),
    }
