import re
from urllib.parse import urlparse, parse_qs

import requests

from config import YOUTUBE_API_KEY, YOUTUBE_BASE_URL


def safe_int(value):
    try:
        return int(value)
    except Exception:
        return 0


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"<.*?>", "", str(text))
    text = text.replace("&amp;", "&")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    return text.strip()


def extract_video_id(url):
    """
    Supports:
    - youtube.com/watch?v=
    - youtu.be/
    - youtube.com/shorts/
    - youtube.com/embed/
    """
    try:
        parsed = urlparse(url.strip())

        if parsed.hostname in ["youtu.be", "www.youtu.be"]:
            return parsed.path.strip("/")

        if parsed.hostname and "youtube.com" in parsed.hostname:
            query = parse_qs(parsed.query)

            if "v" in query:
                return query["v"][0]

            shorts_match = re.search(r"/shorts/([^/?]+)", parsed.path)
            if shorts_match:
                return shorts_match.group(1)

            embed_match = re.search(r"/embed/([^/?]+)", parsed.path)
            if embed_match:
                return embed_match.group(1)

    except Exception:
        return None

    return None


def youtube_get(endpoint, params):
    if not YOUTUBE_API_KEY:
        raise ValueError("Missing YOUTUBE_API_KEY in .streamlit/secrets.toml")

    request_params = dict(params)
    request_params["key"] = YOUTUBE_API_KEY

    response = requests.get(
        f"{YOUTUBE_BASE_URL}/{endpoint}",
        params=request_params,
        timeout=20
    )

    if response.status_code != 200:
        raise RuntimeError(f"YouTube API error: {response.text}")

    return response.json()


def get_video_details(video_url_or_id):
    """
    Returns raw YouTube facts only.
    No scores. No AI. No strategy.
    """
    video_id = extract_video_id(video_url_or_id) or video_url_or_id.strip()

    data = youtube_get(
        "videos",
        {
            "part": "snippet,statistics,contentDetails",
            "id": video_id
        }
    )

    items = data.get("items", [])
    if not items:
        return None

    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})

    thumbnails = snippet.get("thumbnails", {})
    thumbnail = (
        thumbnails.get("maxres", {}).get("url")
        or thumbnails.get("high", {}).get("url")
        or thumbnails.get("medium", {}).get("url")
        or thumbnails.get("default", {}).get("url")
    )

    return {
        "video_id": video_id,
        "title": clean_text(snippet.get("title")),
        "description": clean_text(snippet.get("description")),
        "channel_title": clean_text(snippet.get("channelTitle")),
        "channel_id": snippet.get("channelId", ""),
        "published_at": snippet.get("publishedAt", ""),
        "thumbnail": thumbnail,
        "views": safe_int(stats.get("viewCount")),
        "likes": safe_int(stats.get("likeCount")),
        "comments": safe_int(stats.get("commentCount")),
        "duration": item.get("contentDetails", {}).get("duration", "")
    }


def get_channel_details(channel_id):
    data = youtube_get(
        "channels",
        {
            "part": "snippet,statistics,contentDetails",
            "id": channel_id
        }
    )

    items = data.get("items", [])
    if not items:
        return None

    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    related = item.get("contentDetails", {}).get("relatedPlaylists", {})

    thumbnails = snippet.get("thumbnails", {})
    thumbnail = (
        thumbnails.get("high", {}).get("url")
        or thumbnails.get("medium", {}).get("url")
        or thumbnails.get("default", {}).get("url")
    )

    return {
        "channel_id": channel_id,
        "title": clean_text(snippet.get("title")),
        "description": clean_text(snippet.get("description")),
        "published_at": snippet.get("publishedAt", ""),
        "thumbnail": thumbnail,
        "subscribers": safe_int(stats.get("subscriberCount")),
        "total_views": safe_int(stats.get("viewCount")),
        "video_count": safe_int(stats.get("videoCount")),
        "uploads_playlist_id": related.get("uploads", "")
    }


def get_recent_videos(channel_id, max_results=12):
    channel = get_channel_details(channel_id)

    if not channel or not channel.get("uploads_playlist_id"):
        return []

    playlist_data = youtube_get(
        "playlistItems",
        {
            "part": "snippet",
            "playlistId": channel["uploads_playlist_id"],
            "maxResults": max_results
        }
    )

    video_ids = [
        item.get("snippet", {}).get("resourceId", {}).get("videoId")
        for item in playlist_data.get("items", [])
        if item.get("snippet", {}).get("resourceId", {}).get("videoId")
    ]

    if not video_ids:
        return []

    details = youtube_get(
        "videos",
        {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(video_ids)
        }
    )

    videos = []

    for item in details.get("items", []):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        thumbnails = snippet.get("thumbnails", {})
        thumbnail = (
            thumbnails.get("maxres", {}).get("url")
            or thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
        )

        videos.append(
            {
                "video_id": item.get("id", ""),
                "title": clean_text(snippet.get("title")),
                "description": clean_text(snippet.get("description")),
                "published_at": snippet.get("publishedAt", ""),
                "thumbnail": thumbnail,
                "views": safe_int(stats.get("viewCount")),
                "likes": safe_int(stats.get("likeCount")),
                "comments": safe_int(stats.get("commentCount")),
                "duration": item.get("contentDetails", {}).get("duration", "")
            }
        )

    return videos


def get_full_youtube_context(video_url):
    """
    Main function for Stratify 2.0.

    Input:
    YouTube URL

    Output:
    Video + channel + recent videos.
    """
    video = get_video_details(video_url)

    if not video:
        return None

    channel = get_channel_details(video["channel_id"])
    recent_videos = get_recent_videos(video["channel_id"], max_results=12)

    return {
        "video": video,
        "channel": channel,
        "recent_videos": recent_videos
    }

def search_videos(query, max_results=15, order="relevance"):
    data = youtube_get(
        "search",
        {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "order": order,
        }
    )

    video_ids = [
        item.get("id", {}).get("videoId")
        for item in data.get("items", [])
        if item.get("id", {}).get("videoId")
    ]

    if not video_ids:
        return []

    details = youtube_get(
        "videos",
        {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(video_ids),
        }
    )

    videos = []

    for item in details.get("items", []):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        thumbnails = snippet.get("thumbnails", {})

        thumbnail = (
            thumbnails.get("maxres", {}).get("url")
            or thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
        )

        videos.append(
            {
                "video_id": item.get("id", ""),
                "title": clean_text(snippet.get("title")),
                "description": clean_text(snippet.get("description")),
                "channel_title": clean_text(snippet.get("channelTitle")),
                "channel_id": snippet.get("channelId", ""),
                "published_at": snippet.get("publishedAt", ""),
                "thumbnail": thumbnail,
                "views": safe_int(stats.get("viewCount")),
                "likes": safe_int(stats.get("likeCount")),
                "comments": safe_int(stats.get("commentCount")),
                "duration": item.get("contentDetails", {}).get("duration", ""),
            }
        )

    return videos