import subprocess
from pathlib import Path


TEMP_CLIPS = Path("temp_clips")
TEMP_CLIPS.mkdir(exist_ok=True)


FFMPEG_PATH = r"C:\Users\rahul\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"


def extract_intro_clip(video_path, seconds=8):

    video_path = Path(video_path)

    output_path = TEMP_CLIPS / f"{video_path.stem}_intro.mp4"

    command = [

        FFMPEG_PATH,

        "-y",

        "-i",
        str(video_path),

        "-t",
        str(seconds),

        "-c",
        "copy",

        str(output_path)
    ]

    try:

        subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        return {

            "status": "success",

            "clip_path": str(output_path)

        }

    except subprocess.CalledProcessError as e:

        return {

            "status": "error",

            "message": e.stderr
        }

    except Exception as e:

        return {

            "status": "error",

            "message": str(e)
        }