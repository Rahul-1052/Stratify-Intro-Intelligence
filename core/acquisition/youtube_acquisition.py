import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List


CLIP_DIR = Path("temp_clips")
CLIP_DIR.mkdir(exist_ok=True)

DEFAULT_INTRO_SECONDS = 15


def _run_command(command: List[str]) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": command,
        }

    except Exception as exc:
        return {
            "success": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "command": command,
        }


def _build_output_path() -> Path:
    return CLIP_DIR / f"intro_{uuid.uuid4().hex}.mp4"


def _yt_dlp_base_command(
    url: str,
    output_path: Path,
    intro_seconds: int,
) -> List[str]:
    return [
        sys.executable,
        "-m",
        "yt_dlp",
        "--force-overwrites",
        "--no-playlist",
        "--download-sections",
        f"*00:00-{intro_seconds}",
        "-f",
        "bv*[height<=720]+ba/b[height<=720]/best",
        "--merge-output-format",
        "mp4",
        "-o",
        str(output_path),
        url,
    ]


def _try_plain_yt_dlp(
    url: str,
    output_path: Path,
    intro_seconds: int,
) -> Dict[str, Any]:
    command = _yt_dlp_base_command(
        url=url,
        output_path=output_path,
        intro_seconds=intro_seconds,
    )
    return _run_command(command)


def _try_browser_cookies(
    url: str,
    output_path: Path,
    browser: str,
    intro_seconds: int,
) -> Dict[str, Any]:
    command = _yt_dlp_base_command(
        url=url,
        output_path=output_path,
        intro_seconds=intro_seconds,
    )

    command[3:3] = [
        "--cookies-from-browser",
        browser,
    ]

    return _run_command(command)


def _valid_output(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def _attempt_summary(
    strategy: str,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "strategy": strategy,
        "success": bool(result.get("success")),
        "returncode": result.get("returncode"),
        "stderr": str(result.get("stderr", "")).strip(),
        "stdout": str(result.get("stdout", "")).strip(),
    }


def acquire_intro_clip(
    url: str,
    intro_seconds: int = DEFAULT_INTRO_SECONDS,
) -> Dict[str, Any]:
    """
    Acquire only the requested opening section of a YouTube video.

    Strategies:
    1. Plain yt-dlp using the current Python interpreter.
    2. Edge browser cookies.
    3. Chrome browser cookies.

    The function returns a stable dictionary and never raises downloader
    exceptions to callers.
    """

    normalized_url = str(url or "").strip()

    if not normalized_url:
        return {
            "status": "failed",
            "clip_path": "",
            "method": "",
            "warnings": ["A YouTube URL is required."],
            "attempts": [],
        }

    if intro_seconds <= 0:
        return {
            "status": "failed",
            "clip_path": "",
            "method": "",
            "warnings": ["intro_seconds must be greater than zero."],
            "attempts": [],
        }

    attempts = []

    output_path = _build_output_path()
    plain_result = _try_plain_yt_dlp(
        url=normalized_url,
        output_path=output_path,
        intro_seconds=intro_seconds,
    )
    attempts.append(_attempt_summary("plain_yt_dlp", plain_result))

    if _valid_output(output_path):
        return {
            "status": "success",
            "clip_path": str(output_path),
            "method": "plain_yt_dlp",
            "warnings": [],
            "attempts": attempts,
        }

    for browser in ("edge", "chrome"):
        output_path = _build_output_path()

        browser_result = _try_browser_cookies(
            url=normalized_url,
            output_path=output_path,
            browser=browser,
            intro_seconds=intro_seconds,
        )
        attempts.append(
            _attempt_summary(f"{browser}_cookies", browser_result)
        )

        if _valid_output(output_path):
            return {
                "status": "success",
                "clip_path": str(output_path),
                "method": f"{browser}_cookies",
                "warnings": [],
                "attempts": attempts,
            }

    final_error = next(
        (
            attempt.get("stderr")
            for attempt in reversed(attempts)
            if attempt.get("stderr")
        ),
        "Unknown download failure.",
    )

    return {
        "status": "failed",
        "clip_path": "",
        "method": "",
        "warnings": [
            "Could not acquire intro clip from YouTube.",
            final_error,
        ],
        "attempts": attempts,
    }