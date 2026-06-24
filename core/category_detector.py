import re


def detect_video_category(video):
    title = video.get("title", "")
    description = video.get("description", "")

    text = f"{title} {description}"
    text = re.sub(r"\s+", " ", text).strip()

    return {
        "search_query": title,
        "category_source": "video_title",
        "confidence": "basic",
        "reason": "Using the video title as the first niche search query. Later this will use VLM + transcript + metadata.",
    }