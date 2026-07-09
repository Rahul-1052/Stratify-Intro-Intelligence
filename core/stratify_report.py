from core.benchmark_collector import collect_benchmark_videos
from core.benchmark_feature_extractor import extract_benchmark_features
from core.content_understanding import understand_content
from core.evidence_engine import build_evidence
from core.experiment_engine import generate_experiment_board
from core.intro_observer import observe_intro
from core.pattern_discovery import discover_patterns
from core.pipeline import analyze_intro_pipeline
from core.reasoning import (
    build_evidence_graph,
    compare_creator_decisions,
    infer_benchmark_decisions,
    infer_creator_decisions,
)
from core.youtube_client import get_full_youtube_context
from core.brain import build_stratify_brain


def _empty_benchmark():
    return {
        "query": "",
        "benchmark_anchor": "",
        "query_scores": {},
        "search_queries_used": [],
        "top_performers": [],
        "lower_performers": [],
        "all_candidates": [],
    }


def _successful_feature_count(items):
    return sum(
        bool(item.get("features", {}).get("feature_summary"))
        for item in items or []
        if isinstance(item, dict)
    )


def run_stratify_report(
    url,
    intro_seconds=15,
    frame_fps=1,
    progress_callback=None,
):
    warnings = []
    brain_report = {}

    video_understanding = {
        "status": "unavailable",
        "understanding": {},
        "warnings": [],
    }

    reasoning = {
        "user_decisions": {},
        "benchmark_decisions": {},
        "decision_comparison": {},
        "evidence_graph": {},
    }

    def progress(message):
        if not progress_callback:
            return
        try:
            progress_callback(message)
        except Exception:
            pass

    try:
        progress("Understanding video context...")
        data = get_full_youtube_context(url)

        if data is None:
            return {
                "status": "failed",
                "warnings": ["Could not fetch video data from YouTube."],
                "brain_report": brain_report,
                "video_understanding": video_understanding,
                "reasoning": reasoning,
            }

        video = data.get("video", {})
        channel = data.get("channel", {})
        recent_videos = data.get("recent_videos", [])

        vision = {}
        feature_report = {}
        category = {}
        frames = []

        intro_observation = {
            "status": "unavailable",
            "observation": {},
            "provider": "",
            "warnings": ["Intro frames were not available for observation."],
        }

        progress("Watching and analyzing your intro...")
        intro_result = analyze_intro_pipeline(
            video=video,
            url=url,
            intro_seconds=intro_seconds,
            frame_fps=frame_fps,
        )

        if intro_result.get("status") == "success":
            frames = intro_result.get("frames", [])
            vision = intro_result.get("vision", {})
            feature_report = intro_result.get("features", {})

            video_understanding = {
                "status": "success",
                "understanding": intro_result.get("understanding", {}),
                "warnings": intro_result.get("warnings", []),
            }

            progress("Inferring creator decisions...")
            reasoning["user_decisions"] = infer_creator_decisions(
                video_understanding.get("understanding", {})
            )

            intro_observation = observe_intro(
                frames,
                video=video,
                timeout_seconds=20,
            )

            for warning in intro_observation.get("warnings", []):
                warnings.append(f"Intro observation: {warning}")

            for warning in video_understanding.get("warnings", []):
                warnings.append(f"Video understanding: {warning}")

            progress("Understanding content...")
            try:
                category = understand_content(
                    video=video,
                    intro_observation=video_understanding.get("understanding", {}),
                    timeout_seconds=20,
                )
            except Exception as exc:
                category = {}
                warnings.append(f"Content understanding failed: {str(exc)}")

        else:
            warning = (
                f"Intro pipeline failed at {intro_result.get('stage', 'unknown')}: "
                f"{intro_result.get('error', 'Unknown error.')}"
            )
            warnings.append(warning)

            progress("Understanding content from metadata...")
            try:
                category = understand_content(
                    video=video,
                    intro_observation={},
                    timeout_seconds=20,
                )
            except Exception as exc:
                category = {}
                warnings.append(f"Content understanding failed: {str(exc)}")

        progress("Discovering benchmark context...")
        try:
            benchmark = collect_benchmark_videos(
                category,
                user_video_id=video.get("video_id"),
                max_results=30,
            )
        except Exception as exc:
            benchmark = _empty_benchmark()
            warnings.append(f"Benchmark discovery failed: {str(exc)}")

        progress("Watching benchmark intros...")
        benchmark_features = {"top_performers": [], "lower_performers": []}

        for group_name in ("top_performers", "lower_performers"):
            requested = benchmark.get(group_name, [])[:3]

            try:
                extracted = extract_benchmark_features(
                    requested,
                    intro_seconds=intro_seconds,
                    frame_fps=frame_fps,
                )
            except Exception as exc:
                extracted = []
                warnings.append(
                    f"{group_name.replace('_', ' ').title()} extraction failed: "
                    f"{str(exc)}"
                )

            benchmark_features[group_name] = extracted

            if requested and _successful_feature_count(extracted) == 0:
                warnings.append(
                    f"No {group_name.replace('_', ' ')} intros could be analyzed."
                )

        progress("Reasoning over creator decisions...")
        reasoning["benchmark_decisions"] = infer_benchmark_decisions(
            benchmark_features
        )

        reasoning["decision_comparison"] = compare_creator_decisions(
            user_decisions=reasoning.get("user_decisions", {}),
            benchmark_decisions=reasoning.get("benchmark_decisions", {}),
        )

        reasoning["evidence_graph"] = build_evidence_graph(
            intro_understanding=video_understanding.get("understanding", {}),
            user_decisions=reasoning.get("user_decisions", {}),
            benchmark_decisions=reasoning.get("benchmark_decisions", {}),
            decision_comparison=reasoning.get("decision_comparison", {}),
        )

        evidence = build_evidence(
            video=video,
            channel=channel,
            recent_videos=recent_videos,
            intro_feature_report=feature_report,
            intro_observation=intro_observation,
            benchmark=benchmark,
            benchmark_features=benchmark_features,
            category=category,
            transcript=data.get("transcript"),
            context=data.get("context"),
            warnings=warnings,
        )

        progress("Comparing stronger and weaker intros...")
        patterns = discover_patterns(
            benchmark_features["top_performers"],
            benchmark_features["lower_performers"],
            feature_report,
        )

        brain_report = build_stratify_brain(
            patterns=patterns,
            category=category,
            benchmark=benchmark,
        )

        progress("Building experiment board...")
        experiment_board = generate_experiment_board(patterns)

        return {
            "status": "partial" if warnings else "success",
            "warnings": warnings,
            "intro_seconds": intro_seconds,
            "video": video,
            "channel": channel,
            "recent_videos": recent_videos,
            "category": category,
            "benchmark": benchmark,
            "benchmark_features": benchmark_features,
            "evidence": evidence,
            "patterns": patterns,
            "brain_report": brain_report,
            "experiment_board": experiment_board,
            "feature_report": feature_report,
            "vision": vision,
            "video_understanding": video_understanding,
            "intro_observation": intro_observation,
            "reasoning": reasoning,
            "frames": frames,
        }

    except Exception as exc:
        return {
            "status": "failed",
            "warnings": [f"Unexpected Stratify error: {str(exc)}"],
            "brain_report": brain_report,
            "video_understanding": video_understanding,
            "reasoning": reasoning,
        }