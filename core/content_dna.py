import re


def _lower(text):
    return str(text or "").lower()


def _top_titles(recent_videos, limit=8):
    videos = sorted(
        recent_videos or [],
        key=lambda v: v.get("views", 0),
        reverse=True
    )
    return [v.get("title", "") for v in videos[:limit]]


def _combined_text(video, channel, recent_videos):
    return " ".join(
        [
            video.get("title", ""),
            video.get("description", ""),
            channel.get("title", ""),
            channel.get("description", ""),
            " ".join(_top_titles(recent_videos, 8)),
        ]
    ).lower()


def _detect_content_world(video, channel, recent_videos):
    text = _combined_text(video, channel, recent_videos)

    rules = [
        ("cinematic moments and character-driven stories", ["movie", "film", "scene", "scenes", "series", "cast", "episode", "trailer", "breaking bad", "blacklist"]),
        ("competitive gaming and high-pressure gameplay", ["gameplay", "valorant", "fortnite", "rank", "clutch", "match", "agent"]),
        ("creator education and practical improvement", ["how to", "tutorial", "guide", "tips", "learn", "mistakes", "career"]),
        ("food, taste, and cooking experiences", ["recipe", "cooking", "chef", "food", "kitchen", "dish"]),
        ("sports, competition, and performance moments", ["race", "match", "league", "final", "championship", "team"]),
        ("music, performance, and fan connection", ["song", "music", "lyrics", "album", "singer", "concert"]),
        ("business, strategy, and decision-making content", ["startup", "business", "marketing", "growth", "sales", "strategy"]),
    ]

    for label, keywords in rules:
        if any(word in text for word in keywords):
            return label

    return "recognizable creator content"


def _detect_emotional_style(video, recent_videos):
    text = _lower(video.get("title", "")) + " " + _lower(video.get("description", ""))
    text += " " + _lower(" ".join(_top_titles(recent_videos, 8)))

    if any(w in text for w in ["badass", "brutal", "deadliest", "terrifying", "attack", "killing", "empire", "death", "wrong"]):
        return {
            "label": "intense, dramatic, and high-stakes",
            "feeling": "power, danger, tension, and emotional payoff",
            "viewer_feeling": "Viewers come in expecting something strong to happen, and the content works best when that feeling arrives quickly."
        }

    if any(w in text for w in ["funny", "hilarious", "comedy", "laugh", "unhinged"]):
        return {
            "label": "playful, comedic, and reaction-driven",
            "feeling": "humor, surprise, awkwardness, and replayable reactions",
            "viewer_feeling": "Viewers come in expecting a moment they can laugh at, quote, or share."
        }

    if any(w in text for w in ["secret", "truth", "never", "mistake", "revealed", "could never"]):
        return {
            "label": "curiosity-driven and suspenseful",
            "feeling": "mystery, anticipation, and unanswered questions",
            "viewer_feeling": "Viewers come in because they want the answer, reveal, or hidden context."
        }

    if any(w in text for w in ["guide", "how to", "tips", "learn", "explained"]):
        return {
            "label": "helpful, clear, and educational",
            "feeling": "clarity, progress, and practical improvement",
            "viewer_feeling": "Viewers come in wanting to leave smarter, more capable, or less confused."
        }

    return {
        "label": "clear, familiar, and easy to understand",
        "feeling": "recognition, comfort, and simple payoff",
        "viewer_feeling": "Viewers come in because the topic feels familiar and easy to click."
    }


def _detect_audience_pull(video, recent_videos):
    text = " ".join(_top_titles(recent_videos, 10)).lower()
    title = _lower(video.get("title", ""))
    all_text = text + " " + title

    if any(w in all_text for w in ["breaking bad", "blacklist", "spider-man", "ghostbusters", "karate kid", "the boys"]):
        return {
            "pull": "familiar characters, iconic moments, and scenes viewers already care about",
            "why": "The audience does not need to be educated first. They already have emotional memory connected to the characters and moments."
        }

    if any(w in all_text for w in ["how to", "guide", "tips", "mistakes"]):
        return {
            "pull": "practical improvement and clear takeaways",
            "why": "The audience is looking for help, clarity, or a shortcut to getting better."
        }

    if any(w in all_text for w in ["challenge", "survive", "win", "rank"]):
        return {
            "pull": "tension, stakes, and outcome-driven entertainment",
            "why": "The audience wants to see what happens, who wins, or how far the creator can go."
        }

    if any(w in all_text for w in ["review", "best", "worst", "vs"]):
        return {
            "pull": "comparison, judgment, and viewer opinion",
            "why": "The audience wants to agree, disagree, rank, debate, or validate their own opinion."
        }

    return {
        "pull": "clear topics, familiar promises, and easy reasons to click",
        "why": "The audience connects faster when the video promise is obvious before they have to think."
    }


def _detect_repeatable_success_pattern(video, recent_videos):
    text = _lower(video.get("title", "")) + " " + _lower(" ".join(_top_titles(recent_videos, 10)))

    patterns = []

    if any(w in text for w in ["badass", "brutal", "deadliest", "terrifying", "death", "attack", "empire"]):
        patterns.append("powerful emotional stakes")

    if any(w in text for w in ["breaking bad", "blacklist", "spider-man", "ghostbusters", "karate kid", "the boys"]):
        patterns.append("recognizable characters or franchises")

    if any(w in text for w in ["never", "wrong", "secret", "truth", "forgot", "thought"]):
        patterns.append("titles that create curiosity or memory")

    if any(w in text for w in ["best", "moments", "scenes", "every time"]):
        patterns.append("compilation-style packaging that promises the best parts upfront")

    if not patterns:
        patterns = [
            "clear viewer promise",
            "familiar topic framing",
            "repeatable emotional payoff"
        ]

    return patterns[:4]


def _clean_sentence(text):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text


def generate_content_dna(video, channel, recent_videos):
    """
    Stratify 2.0 Content DNA V2.
    Human creator intelligence.
    No ML jargon. No scores. No clusters.
    """

    channel_name = channel.get("title", "This creator")
    video_title = video.get("title", "this video")

    content_world = _detect_content_world(video, channel, recent_videos)
    emotional_style = _detect_emotional_style(video, recent_videos)
    audience_pull = _detect_audience_pull(video, recent_videos)
    repeatable_patterns = _detect_repeatable_success_pattern(video, recent_videos)

    creative_identity = _clean_sentence(
        f"{channel_name} specializes in {content_world}. "
        f"The channel is strongest when it turns familiar material into moments that feel worth reliving. "
        f"This is not just content people watch once; it is content built around recognition, memory, and emotional payoff."
    )

    visual_personality = _clean_sentence(
        f"The content feels {emotional_style['label']}. "
        f"Its strongest emotional lane is {emotional_style['feeling']}. "
        f"{emotional_style['viewer_feeling']}"
    )

    audience_connection = _clean_sentence(
        f"Viewers connect because of {audience_pull['pull']}. "
        f"{audience_pull['why']} "
        f"For this video, the title promises a powerful reason to watch: {video_title}."
    )

    creative_signature = _clean_sentence(
        "The creative superpower is emotional repackaging. "
        "The channel takes moments viewers may already know and makes them feel important again. "
        "That is powerful because the audience is not only watching for information; they are watching to feel the moment again."
    )

    repeatable_pattern = (
        "Your strongest repeatable pattern appears to be:\n\n"
        + "\n".join([f"• {pattern.capitalize()}" for pattern in repeatable_patterns])
        + "\n\nKeep repeating the emotional promise behind these patterns, not the exact same titles."
    )

    return {
        "creative_identity": creative_identity,
        "visual_personality": visual_personality,
        "audience_connection": audience_connection,
        "creative_signature": creative_signature,
        "repeatable_pattern": repeatable_pattern,
    }