import os
import uuid
import subprocess
from pathlib import Path


CLIP_DIR = Path("temp_clips")
CLIP_DIR.mkdir(exist_ok=True)

DEFAULT_INTRO_SECONDS = 15


def _run_command(command):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except Exception as exc:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(exc),
        }


def _build_output_path():
    return CLIP_DIR / f"intro_{uuid.uuid4().hex}.mp4"


def _yt_dlp_base_command(url, output_path):
    return [
        "yt-dlp",
        "--force-overwrites",
        "--no-playlist",
        "--download-sections",
        f"*00:00-{DEFAULT_INTRO_SECONDS}",
        "-f",
        "bv*[height<=720]+ba/b[height<=720]/best",
        "--merge-output-format",
        "mp4",
        "-o",
        str(output_path),
        url,
    ]


def _try_plain_yt_dlp(url, output_path):
    command = _yt_dlp_base_command(url, output_path)
    return _run_command(command)


def _try_browser_cookies(url, output_path, browser):
    command = _yt_dlp_base_command(url, output_path)
    command.insert(1, "--cookies-from-browser")
    command.insert(2, browser)
    return _run_command(command)


def acquire_intro_clip(url, intro_seconds=DEFAULT_INTRO_SECONDS):
    """
    Reliable intro acquisition.

    Tries:
    1. plain yt-dlp
    2. Chrome cookies
    3. Edge cookies

    Returns a stable object.
    """

    global DEFAULT_INTRO_SECONDS
    DEFAULT_INTRO_SECONDS = intro_seconds

    output_path = _build_output_path()

    attempts = []

    plain = _try_plain_yt_dlp(url, output_path)
    attempts.append(("plain_yt_dlp", plain))

    if output_path.exists() and output_path.stat().st_size > 0:
        return {
            "status": "success",
            "clip_path": str(output_path),
            "method": "plain_yt_dlp",
            "warnings": [],
            "attempts": attempts,
        }

    for browser in ["chrome", "edge"]:
        output_path = _build_output_path()

        result = _try_browser_cookies(url, output_path, browser)
        attempts.append((f"{browser}_cookies", result))

        if output_path.exists() and output_path.stat().st_size > 0:
            return {
                "status": "success",
                "clip_path": str(output_path),
                "method": f"{browser}_cookies",
                "warnings": [],
                "attempts": attempts,
            }

    warning = attempts[-1][1].get("stderr", "Unknown download failure.")

    return {
        "status": "failed",
        "clip_path": "",
        "method": "",
        "warnings": [
            "Could not acquire intro clip from YouTube.",
            warning,
        ],
        "attempts": attempts,
    }