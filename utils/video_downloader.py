import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse


TEMP_VIDEO_DIR = Path("temp_videos")
TEMP_VIDEO_DIR.mkdir(exist_ok=True)


YOUTUBE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_youtube_video_id(url_or_id):
    """
    Extract a YouTube video id from common desktop, mobile, short, and embed URLs.
    """
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
    """
    Convert supported YouTube URL shapes into the canonical watch URL used by
    benchmark downloads.
    """
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


def download_video(url):
    """
    Downloads a YouTube video locally for intro extraction.

    Returns:
    {
        "status": "success",
        "video_path": "temp_videos/video_id.mp4",
        "video_id": "VIDEO_ID",
        "title": "Video title",
        "normalized_url": "https://www.youtube.com/watch?v=VIDEO_ID"
    }

    On failure, returns status="error" with a detailed message and context.
    """
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
        from yt_dlp import YoutubeDL
        from yt_dlp.utils import DownloadError
    except ImportError as e:
        return _error_response(
            f"yt-dlp is not installed or could not be imported: {str(e)}",
            original_url=original_url,
            normalized_url=normalized_url,
            video_id=video_id,
            error_type="missing_dependency",
        )

    ydl_opts = {
        "format": "mp4[height<=720]/bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "merge_output_format": "mp4",
        "outtmpl": str(TEMP_VIDEO_DIR / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "windowsfilenames": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(normalized_url, download=True)
            video_path = _downloaded_file_path(info, ydl)

        if not video_path:
            return _error_response(
                "Video download completed, but Stratify could not locate the downloaded file.",
                original_url=original_url,
                normalized_url=normalized_url,
                video_id=video_id,
                error_type="downloaded_file_missing",
            )

        return {
            "status": "success",
            "video_path": str(video_path),
            "video_id": info.get("id") or video_id,
            "title": info.get("title", ""),
            "normalized_url": normalized_url,
            "original_url": original_url,
        }

    except DownloadError as e:
        return _error_response(
            f"yt-dlp could not download this video: {str(e)}",
            original_url=original_url,
            normalized_url=normalized_url,
            video_id=video_id,
            error_type="download_error",
        )

    except Exception as e:
        return _error_response(
            f"Unexpected downloader error: {str(e)}",
            original_url=original_url,
            normalized_url=normalized_url,
            video_id=video_id,
            error_type=type(e).__name__,
        )