import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2

FFMPEG_PATH = r"C:\Users\rahul\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
TEMP_FRAMES = Path("temp_frames")
TEMP_FRAMES.mkdir(exist_ok=True)


@dataclass(frozen=True)
class SamplingConfig:
    early_window_seconds: float = 3.0
    early_interval_seconds: float = 0.5
    later_interval_seconds: float = 1.0
    maximum_samples: int = 20


DEFAULT_SAMPLING = SamplingConfig()


def build_sampling_timestamps(duration, config=None):
    config = config or DEFAULT_SAMPLING
    duration = max(float(duration or 0), 0.0)
    timestamps, current = [], 0.0
    while current < duration and len(timestamps) < config.maximum_samples:
        timestamps.append(round(current, 3))
        current += config.early_interval_seconds if current < config.early_window_seconds else config.later_interval_seconds
    return timestamps or [0.0]


def _clip_duration(path):
    capture = cv2.VideoCapture(str(path))
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        return count / fps if fps and count else 0.0
    finally:
        capture.release()


def extract_frames_from_clip(clip_path, fps=1, sampling_config=None):
    clip_path = Path(clip_path)
    output_folder = TEMP_FRAMES / clip_path.stem
    output_folder.mkdir(parents=True, exist_ok=True)
    for stale_frame in output_folder.glob("frame_*.jpg"):
        stale_frame.unlink()
    config = sampling_config or DEFAULT_SAMPLING
    duration = _clip_duration(clip_path)
    timestamps = build_sampling_timestamps(duration, config)
    expression = "+".join(f"between(t,{value:.3f},{value + 0.04:.3f})" for value in timestamps)
    output_pattern = output_folder / "frame_%03d.jpg"
    command = [FFMPEG_PATH, "-y", "-i", str(clip_path), "-vf", f"select='{expression}'", "-vsync", "vfr", str(output_pattern)]
    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
        frames = sorted(output_folder.glob("frame_*.jpg"))
        effective = timestamps[:len(frames)]
        samples = [{"path": str(frame), "timestamp": timestamp} for frame, timestamp in zip(frames, effective)]
        return {
            "status": "success", "frames": [item["path"] for item in samples],
            "samples": samples, "timestamps": effective, "frame_count": len(samples),
            "sampling_plan": {"strategy": "adaptive_early_intro", "requested_fps": fps,
                              "clip_duration": round(duration, 3), "requested_timestamps": timestamps,
                              "effective_timestamps": effective, "config": asdict(config)},
        }
    except subprocess.CalledProcessError as exc:
        return {"status": "error", "error_type": "frame_extract_failed", "message": exc.stderr}
    except Exception as exc:
        return {"status": "error", "error_type": "frame_extract_failed", "message": str(exc)}
