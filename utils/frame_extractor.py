import subprocess
from pathlib import Path

FFMPEG_PATH = r"C:\Users\rahul\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"

TEMP_FRAMES = Path("temp_frames")
TEMP_FRAMES.mkdir(exist_ok=True)


def extract_frames_from_clip(clip_path, fps=1):
    clip_path = Path(clip_path)

    output_folder = TEMP_FRAMES / clip_path.stem
    output_folder.mkdir(parents=True, exist_ok=True)

    output_pattern = output_folder / "frame_%03d.jpg"

    command = [
        FFMPEG_PATH,
        "-y",
        "-i", str(clip_path),
        "-vf", f"fps={fps}",
        str(output_pattern)
    ]

    try:
        subprocess.run(command, capture_output=True, text=True, check=True)

        frames = sorted(output_folder.glob("*.jpg"))

        return {
            "status": "success",
            "frames": [str(frame) for frame in frames],
            "frame_count": len(frames)
        }

    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": e.stderr}

    except Exception as e:
        return {"status": "error", "message": str(e)}