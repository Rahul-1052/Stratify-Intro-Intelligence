from core.benchmark_collector import collect_benchmark_videos
from core.benchmark_signature import build_benchmark_signature
from core.benchmark_feature_extractor import extract_benchmark_features
from core.benchmark_qualification import qualify_observed_benchmarks
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
    learn_benchmark_patterns,
    build_creative_reasoning,
)
from core.youtube_client import get_full_youtube_context
from core.brain import build_stratify_brain
from core.creator_report import build_creator_report
from core.source_context import resolve_source_context


def _empty_benchmark():
    return {
        "query": "",
        "benchmark_anchor": "",
        "query_scores": {},
        "search_queries_used": [],
        "top_performers": [],
        "lower_performers": [],
        "all_candidates": [],
        "raw_candidates": [],
        "shortlist": [],
        "qualification_diagnostics": [],
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
    uploaded_video_path=None,
    local_source_type="uploaded_file",
    no_network=False,
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
        "pattern_learning": {},
    }

    def progress(message):
        if not progress_callback:
            return
        try:
            progress_callback(message)
        except Exception:
            pass

    try:
        source_context = resolve_source_context(
            url=url, local_path=uploaded_video_path or "",
            local_source_type=local_source_type,
        )
        if source_context.source_type == "youtube_url":
            if no_network:
                return {
                    "status": "failed", "stage": "source_context_unavailable",
                    "warnings": ["YouTube source analysis is unavailable in no-network mode."],
                    "brain_report": brain_report, "video_understanding": video_understanding,
                    "reasoning": reasoning, "source_context": source_context.to_dict(),
                }
            progress("Understanding video context...")
            try:
                data = get_full_youtube_context(url)
            except Exception as exc:
                return {
                    "status": "failed", "stage": "source_context_unavailable",
                    "warnings": [str(exc)], "error": str(exc),
                    "brain_report": brain_report, "video_understanding": video_understanding,
                    "reasoning": reasoning, "source_context": source_context.to_dict(),
                }
            if data is None:
                return {
                    "status": "failed", "stage": "source_context_unavailable",
                    "warnings": ["Could not fetch video data from YouTube."],
                    "brain_report": brain_report, "video_understanding": video_understanding,
                    "reasoning": reasoning, "source_context": source_context.to_dict(),
                }
            source_context.metadata_status = "available"
            source_context.acquisition_status = "pending"
            source_context.benchmark_context_status = "available"
        else:
            if source_context.acquisition_status == "failed":
                return {
                    "status": "failed", "stage": "local_source_unavailable",
                    "warnings": source_context.warnings,
                    "brain_report": brain_report, "video_understanding": video_understanding,
                    "reasoning": reasoning, "source_context": source_context.to_dict(),
                }
            data = {
                "video": source_context.video_metadata(), "channel": {},
                "recent_videos": [], "transcript": None, "context": None,
            }
            warnings.extend(source_context.warnings)

        video = data.get("video", {})
        channel = data.get("channel", {})
        recent_videos = data.get("recent_videos", [])

        vision = {}
        feature_report = {}
        category = {}
        frames = []
        acquisition = {}
        semantic_observation = {}
        creative_structure = {}
        creative_understanding = {}
        temporal_evidence = {}

        intro_observation = {
            "status": "unavailable",
            "observation": {},
            "provider": "",
            "warnings": ["Intro frames were not available for observation."],
        }

        progress(
            "Analyzing your uploaded video intro..."
            if uploaded_video_path
            else "Watching and analyzing your intro..."
        )

        intro_result = analyze_intro_pipeline(
            video=video,
            url=url,
            intro_seconds=intro_seconds,
            frame_fps=frame_fps,
            local_video_path=uploaded_video_path,
        )

        if intro_result.get("status") == "success":
            source_context.acquisition_status = "completed"
            frames = intro_result.get("frames", [])
            vision = intro_result.get("vision", {})
            feature_report = intro_result.get("features", {})
            acquisition = intro_result.get("acquisition", {})
            semantic_observation = intro_result.get("semantic_observation", {})
            creative_structure = intro_result.get("creative_structure", {})
            creative_understanding = intro_result.get("creative_understanding", {})
            temporal_evidence = intro_result.get("temporal_evidence", {})

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
                vision=vision,
                understanding=video_understanding.get(
                    "understanding",
                    {},
                ),
                timeout_seconds=45,
            )

            for warning in intro_observation.get("warnings", []):
                warnings.append(f"Intro observation: {warning}")

            for warning in video_understanding.get("warnings", []):
                warnings.append(f"Video understanding: {warning}")

            progress("Understanding content...")
            try:
                category = understand_content(
                    video=video,
                    intro_observation={
                        "canonical_observation": intro_observation.get("observation", {}),
                        "understanding": video_understanding.get("understanding", {}),
                        "vision": vision,
                        "features": feature_report,
                    },
                    timeout_seconds=20,
                )
            except Exception as exc:
                category = {}
                warnings.append(f"Content understanding failed: {str(exc)}")

        else:
            source_context.acquisition_status = "failed"
            warnings.append(
                f"Intro pipeline failed at {intro_result.get('stage', 'unknown')}: "
                f"{intro_result.get('error', 'Unknown error.')}"
            )
            acquisition = {
                "source": "uploaded_video" if uploaded_video_path else "youtube",
                "method": "",
                "attempts": intro_result.get("attempts", []),
            }

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

        benchmark_unavailable = source_context.source_type != "youtube_url" or no_network
        progress("Building benchmark evidence profile...")
        try:
            user_benchmark_signature = build_benchmark_signature(
                video=video,
                vision=vision,
                understanding=video_understanding.get(
                    "understanding",
                    {},
                ),
            )
        except Exception as exc:
            user_benchmark_signature = None
            warnings.append(
                f"User benchmark signature failed: {str(exc)}"
            )

        progress("Discovering benchmark context...")
        if benchmark_unavailable:
            benchmark = _empty_benchmark()
            benchmark["status"] = "unavailable"
            benchmark["limitation"] = "Benchmark context is unavailable for this local source."
            warnings.append("Benchmark context is unavailable; recommendations use direct video evidence only.")
        else:
            try:
                benchmark = collect_benchmark_videos(
                    category,
                    user_video_id=video.get("video_id"),
                    max_results=30,
                    user_video=video,
                    user_vision=vision,
                    user_understanding=video_understanding.get(
                        "understanding",
                        {},
                    ),
                    user_signature=user_benchmark_signature,
                )
            except Exception as exc:
                benchmark = _empty_benchmark()
                benchmark["status"] = "unavailable"
                warnings.append(f"Benchmark discovery failed: {str(exc)}")

        progress("Watching benchmark shortlist intros...")
        shortlist = benchmark.get("shortlist", [])
        if benchmark_unavailable:
            observed_shortlist = []
        else:
            try:
                observed_shortlist = extract_benchmark_features(
                    shortlist,
                    intro_seconds=intro_seconds,
                    frame_fps=frame_fps,
                )
            except Exception as exc:
                observed_shortlist = []
                warnings.append(f"Benchmark shortlist observation failed: {str(exc)}")

        progress("Qualifying observed benchmark viewer jobs...")
        qualification = qualify_observed_benchmarks(
            user_video=video,
            user_vision=vision,
            user_understanding=video_understanding.get("understanding", {}),
            user_features=feature_report,
            observed_candidates=observed_shortlist,
            user_content_identity=category.get("content_understanding", {}),
        )
        if benchmark_unavailable:
            qualification["status"] = "unavailable"
            qualification["reason"] = "Benchmark context is unavailable for this local source."
            qualification["eligible_for_directional_learning"] = False
        benchmark["qualification"] = qualification
        benchmark["benchmark_quality"] = qualification.get("benchmark_quality", {})
        benchmark["performance_diagnostics"] = qualification.get("performance_diagnostics", {})
        benchmark["qualification_diagnostics"] = (
            benchmark.get("qualification_diagnostics", [])
            + qualification.get("diagnostics", [])
        )
        benchmark["observed_candidates"] = observed_shortlist
        benchmark_features = {
            "top_performers": qualification.get("top_performers", []),
            "lower_performers": qualification.get("lower_performers", []),
        }
        benchmark["top_performers"] = [
            item.get("video", {}) for item in benchmark_features["top_performers"]
        ]
        benchmark["lower_performers"] = [
            item.get("video", {}) for item in benchmark_features["lower_performers"]
        ]
        if qualification.get("status") != "success":
            warnings.append(
                "Benchmark qualification limited: "
                + qualification.get("reason", "No coherent observed neighborhood was formed.")
            )

        progress("Learning benchmark patterns...")
        reasoning["pattern_learning"] = learn_benchmark_patterns(benchmark_features, min_support=3)

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
            min_support=3,
        )
        if not qualification.get("eligible_for_directional_learning"):
            patterns["recommendations"] = []
            patterns["top_creator_experiments"] = []
            patterns["strongest_opportunities"] = []
            patterns["confidence"] = "limited"
            patterns["confidence_reason"] = (
                "The benchmark set did not meet the independent quality floor for directional learning."
            )
        patterns["benchmark_quality"] = qualification.get("benchmark_quality", {})
        patterns["abstention_reason"] = (
            "insufficient benchmark quality"
            if not qualification.get("eligible_for_directional_learning")
            else (
                "no meaningful feature difference"
                if not patterns.get("recommendations")
                else ""
            )
        )

        brain_report = build_stratify_brain(
            patterns=patterns,
            category=category,
            benchmark=benchmark,
        )

        progress("Building experiment board...")
        experiment_board = generate_experiment_board(patterns)

        partial_report = {
            "intro_observation": intro_observation,
            "feature_report": feature_report,
            "vision": vision,
            "semantic_observation": semantic_observation,
            "temporal_evidence": temporal_evidence,
            "creative_structure": creative_structure,
            "creative_understanding": creative_understanding,
            "video_understanding": video_understanding,
            "benchmark": benchmark,
            "patterns": patterns,
            "source_context": source_context.to_dict(),
        }
        progress("Translating evidence into creative reasoning...")
        reasoning["creative_reasoning"] = build_creative_reasoning(partial_report)
        creator_report = build_creator_report(
            partial_report,
            creative_reasoning=reasoning["creative_reasoning"],
        )

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
            "creator_report": creator_report,
            "feature_report": feature_report,
            "vision": vision,
            "semantic_observation": semantic_observation,
            "temporal_evidence": temporal_evidence,
            "creative_structure": creative_structure,
            "creative_understanding": creative_understanding,
            "video_understanding": video_understanding,
            "intro_observation": intro_observation,
            "reasoning": reasoning,
            "acquisition": acquisition,
            "frames": frames,
            "source_context": source_context.to_dict(),
            "benchmark_context_status": "unavailable" if benchmark_unavailable else "available",
        }

    except Exception as exc:
        return {
            "status": "failed",
            "warnings": [f"Unexpected Stratify error: {str(exc)}"],
            "brain_report": brain_report,
            "video_understanding": video_understanding,
            "reasoning": reasoning,
        }
