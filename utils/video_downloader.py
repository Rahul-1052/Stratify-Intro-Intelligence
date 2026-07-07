import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse


TEMP_VIDEO_DIR = Path("temp_videos")
TEMP_VIDEO_DIR.mkdir(exist_ok=True)

YOUTUBE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_youtube_video_id(url_or_id):
    if not url_or_id:
        return None

    raw_value = str(url_or_id).strip()
    if not raw_value:
        return None

    if YOUTUBE_ID_PATTERN.match(raw_value):
        return raw_value

    try:
        parsed = urlparse(raw_value)
    except Exception:
        return None

    hostname = (parsed.hostname or "").lower()
    path = parsed.path or ""

    if hostname in {"youtu.be", "www.youtu.be"}:
        video_id = path.strip("/").split("/")[0]
        return video_id if YOUTUBE_ID_PATTERN.match(video_id) else None

    if hostname in {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
    }:
        query = parse_qs(parsed.query)
        video_id = query.get("v", [None])[0]
        if video_id and YOUTUBE_ID_PATTERN.match(video_id):
            return video_id

        for pattern in (
            r"^/shorts/([^/?#]+)",
            r"^/embed/([^/?#]+)",
            r"^/live/([^/?#]+)",
            r"^/v/([^/?#]+)",
        ):
            match = re.search(pattern, path)
            if match:
                video_id = match.group(1)
                return video_id if YOUTUBE_ID_PATTERN.match(video_id) else None

    return None


def normalize_youtube_url(url_or_id):
    video_id = extract_youtube_video_id(url_or_id)

    if not video_id:
        raise ValueError(
            "Could not extract a valid YouTube video id from the provided URL."
        )

    return f"https://www.youtube.com/watch?v={video_id}"


def _downloaded_file_path(info, ydl):
    requested_downloads = info.get("requested_downloads") or []

    for download in requested_downloads:
        filepath = download.get("filepath")
        if filepath and Path(filepath).exists():
            return Path(filepath)

    filename = info.get("_filename")
    if filename and Path(filename).exists():
        return Path(filename)

    prepared_filename = ydl.prepare_filename(info)
    if prepared_filename and Path(prepared_filename).exists():
        return Path(prepared_filename)

    video_id = info.get("id")
    if video_id:
        matches = sorted(TEMP_VIDEO_DIR.glob(f"{video_id}.*"))
        if matches:
            return matches[0]

    return None


def _error_response(message, **details):
    response = {
        "status": "error",
        "message": message,
    }
    response.update({key: value for key, value in details.items() if value})
    return response


def _base_ydl_opts(video_id):
    return {
        "format": "bv*[height<=720]+ba/b[height<=720]/best",
        "merge_output_format": "mp4",
        "outtmpl": str(TEMP_VIDEO_DIR / f"{video_id}.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "windowsfilenames": True,
        "retries": 10,
        "fragment_retries": 10,
        "socket_timeout": 30,
        "concurrent_fragment_downloads": 3,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            }
        },
    }


def _download_with_opts(normalized_url, ydl_opts):
    from yt_dlp import YoutubeDL

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(normalized_url, download=True)
        video_path = _downloaded_file_path(info, ydl)

    return info, video_path


def _strategy_plain(video_id):
    return _base_ydl_opts(video_id)


def _strategy_android_only(video_id):
    opts = _base_ydl_opts(video_id)
    opts["extractor_args"] = {
        "youtube": {
            "player_client": ["android"],
        }
    }
    return opts


def _strategy_web_only(video_id):
    opts = _base_ydl_opts(video_id)
    opts["extractor_args"] = {
        "youtube": {
            "player_client": ["web"],
        }
    }
    return opts


def _strategy_chrome_cookies(video_id):
    opts = _base_ydl_opts(video_id)
    opts["cookiesfrombrowser"] = ("chrome",)
    return opts


def _strategy_edge_cookies(video_id):
    opts = _base_ydl_opts(video_id)
    opts["cookiesfrombrowser"] = ("edge",)
    return opts


def download_video(url):
    original_url = str(url or "").strip()

    try:
        video_id = extract_youtube_video_id(original_url)
        normalized_url = normalize_youtube_url(original_url)
    except ValueError as e:
        return _error_response(
            str(e),
            original_url=original_url,
            error_type="invalid_youtube_url",
        )

    try:
        from yt_dlp.utils import DownloadError
    except ImportError as e:
        return _error_response(
            f"yt-dlp is not installed or could not be imported: {str(e)}",
            original_url=original_url,
            normalized_url=normalized_url,
            video_id=video_id,
            error_type="missing_dependency",
        )

    strategies = [
        ("plain_android_web", _strategy_plain),
        ("android_only", _strategy_android_only),
        ("web_only", _strategy_web_only),
        ("chrome_cookies", _strategy_chrome_cookies),
        ("edge_cookies", _strategy_edge_cookies),
    ]

    errors = []

    for strategy_name, strategy_builder in strategies:
        try:
            ydl_opts = strategy_builder(video_id)
            info, video_path = _download_with_opts(normalized_url, ydl_opts)

            if not video_path:
                errors.append(
                    f"{strategy_name}: download completed but file was not found."
                )
                continue

            return {
                "status": "success",
                "video_path": str(video_path),
                "video_id": info.get("id") or video_id,
                "title": info.get("title", ""),
                "normalized_url": normalized_url,
                "original_url": original_url,
                "download_strategy": strategy_name,
            }

        except DownloadError as e:
            errors.append(f"{strategy_name}: {str(e)}")

        except Exception as e:
            errors.append(f"{strategy_name}: {type(e).__name__}: {str(e)}")

    return _error_response(
        "yt-dlp could not download this video after multiple strategies.",
        original_url=original_url,
        normalized_url=normalized_url,
        video_id=video_id,
        error_type="download_error",
        attempts=" | ".join(errors[-5:]),
    )