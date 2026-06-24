def detect_emotional_center(video, context, vision):
    title = video.get("title", "").lower()
    description = video.get("description", "").lower()
    combined = f"{title} {description}"

    # This is V1 logic.
    # Later, this will use real VLM + context intelligence.
    if any(word in combined for word in ["reddington", "blacklist", "badass", "powerful", "mastermind"]):
        center = "calm dominance"
        audience_desire = "to watch someone stay in control when everyone else feels threatened"
        creator_advantage = "turning power, intelligence, and mystery into emotionally satisfying moments"
        growth_direction = "show the strongest display of control earlier in the intro"

    elif any(word in combined for word in ["car", "drive", "driving", "bmw", "porsche", "tesla", "mustang"]):
        center = "freedom, motion, and lifestyle"
        audience_desire = "to feel the experience of speed, escape, and control"
        creator_advantage = "turning movement and atmosphere into an emotional experience"
        growth_direction = "make the first few seconds feel more immersive through sound, motion, or scenery"

    elif any(word in combined for word in ["valorant", "fortnite", "gameplay", "clutch", "rank", "match"]):
        center = "skill, pressure, and respect"
        audience_desire = "to witness high-pressure moments that feel impressive or impossible"
        creator_advantage = "turning gameplay into moments of tension and reward"
        growth_direction = "show the highest-stakes moment sooner before giving context"

    elif any(word in combined for word in ["recipe", "cooking", "food", "chef", "kitchen"]):
        center = "comfort, transformation, and satisfaction"
        audience_desire = "to watch simple ingredients become something desirable"
        creator_advantage = "turning process into comfort and anticipation"
        growth_direction = "show the final result or most satisfying step earlier"

    else:
        center = "clear emotional payoff"
        audience_desire = "to quickly understand why this video is worth watching"
        creator_advantage = "turning familiar ideas into moments that feel meaningful"
        growth_direction = "make the emotional promise visible earlier"

    return {
        "center": center,
        "audience_desire": audience_desire,
        "creator_advantage": creator_advantage,
        "growth_direction": growth_direction
    }