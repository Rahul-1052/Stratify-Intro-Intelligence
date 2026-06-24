def generate_creator_insights(vision, context, emotion):
    center = emotion.get("center", "emotional clarity")
    audience_desire = emotion.get("audience_desire", "a clear reason to keep watching")
    creator_advantage = emotion.get("creator_advantage", "turning familiar ideas into emotionally strong moments")
    growth_direction = emotion.get("growth_direction", "make the emotional promise clear earlier")

    return {
        "viewer_feeling": (
            f"Viewers immediately feel {center.lower()}. "
            "The intro works best when the audience can sense the main emotion before needing explanation."
        ),
        "story_promise": (
            f"The story promise is clear: viewers are here {audience_desire.lower()}. "
            "The viewer should quickly understand what emotional experience this video is offering."
        ),
        "why_they_stay": (
            f"People keep watching because they want {audience_desire.lower()}. "
            "The stronger that feeling appears in the first few seconds, the easier it is for them to commit."
        ),
        "creator_opportunity": (
            f"Your creator advantage is {creator_advantage.lower()}. "
            f"The next opportunity is to {growth_direction.lower()}."
        ),
    }