from core.pipeline import analyze_intro_pipeline
from core.content_understanding import understand_content
from core.intro_observer import observe_intro


def _failure(video, stage, message):
    return {
        "video": video,
        "status": "failed",
        "stage": stage,
        "error": message or "Unknown error.",
    }


def extract_benchmark_features(videos, intro_seconds=15, frame_fps=1):
    results = []

    for video in videos or []:
        video_id = video.get("video_id")

        if not video_id:
            results.append(
                _failure(video, "normalize_url_failed", "Missing video id.")
            )
            continue

        try:
            result = analyze_intro_pipeline(
                video=video,
                intro_seconds=intro_seconds,
                frame_fps=frame_fps,
            )

            if result.get("status") != "success":
                results.append(
                    _failure(
                        video,
                        result.get("stage", "intro_pipeline_failed"),
                        result.get("error"),
                    )
                )
                continue

            canonical_observation = observe_intro(
                result.get("frames", []),
                video=video,
                vision=result.get("vision", {}),
                understanding=result.get("understanding", {}),
                timeout_seconds=35,
            )

            content_identity = understand_content(
                video=video,
                intro_observation={
                    "canonical_observation": canonical_observation.get("observation", {}),
                    "understanding": result.get("understanding", {}),
                    "vision": result.get("vision", {}),
                    "features": result.get("features", {}),
                },
                timeout_seconds=20,
            ).get("content_understanding", {})

            results.append(
                {
                    "video": video,
                    "status": "success",
                    "features": result.get("features", {}),
                    "vision": result.get("vision", {}),
                    "understanding": result.get("understanding", {}),
                    "content_identity": content_identity,
                    "intro_observation": canonical_observation,
                    "frames": result.get("frames", []),
                }
            )

        except Exception as exc:
            results.append(_failure(video, "unexpected", str(exc)))

    return results
