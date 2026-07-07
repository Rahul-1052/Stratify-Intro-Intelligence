from core.pipeline import analyze_intro_pipeline


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

            results.append(
                {
                    "video": video,
                    "status": "success",
                    "features": result.get("features", {}),
                    "vision": result.get("vision", {}),
                    "understanding": result.get("understanding", {}),
                    "frames": result.get("frames", []),
                }
            )

        except Exception as exc:
            results.append(_failure(video, "unexpected", str(exc)))

    return results