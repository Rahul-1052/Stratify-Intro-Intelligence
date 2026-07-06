def build_creator_brain_report(insights, experiments, category=None, benchmark=None):
    category = category or {}
    benchmark = benchmark or {}

    content_understanding = category.get("content_understanding", {})

    return {
        "status": "success" if insights or experiments else "insufficient_evidence",
        "what_stratify_understood": {
            "content_type": content_understanding.get("content_type", category.get("category", "unknown")),
            "topic_or_source": content_understanding.get("topic_or_source", category.get("micro_niche", "unknown")),
            "audience_intent": content_understanding.get("audience_intent", ""),
            "search_queries": category.get("search_queries", []),
        },
        "benchmark_context": {
            "top_count": len(benchmark.get("top_performers", [])),
            "lower_count": len(benchmark.get("lower_performers", [])),
            "candidate_count": benchmark.get("candidate_count", 0),
            "reason": benchmark.get("lower_performer_reason", ""),
        },
        "key_insights": insights,
        "experiment_board": experiments,
    }