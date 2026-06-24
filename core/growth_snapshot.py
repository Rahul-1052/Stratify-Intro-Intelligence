def generate_growth_snapshot(video, channel, recent_videos):

    views = video.get("views", 0)
    likes = video.get("likes", 0)
    comments = video.get("comments", 0)

    subscribers = channel.get("subscribers", 0)

    engagement_rate = 0

    if views > 0:
        engagement_rate = ((likes + comments) / views) * 100

    # Current Momentum

    if views > subscribers * 0.25:
        momentum = (
            "Your content shows strong momentum. "
            "The audience already understands your content style and continues to engage with it consistently."
        )

    elif views > subscribers * 0.10:
        momentum = (
            "Your content has recognizable momentum with room to accelerate. "
            "The foundation is strong and repeatable."
        )

    else:
        momentum = (
            "Your content identity is emerging. "
            "Consistent storytelling and stronger openings may help accelerate growth."
        )

    # Strongest Area

    title = video.get("title", "").lower()

    if any(x in title for x in ["scene", "moments", "best", "badass", "fight"]):

        strongest = (
            "Your biggest strength is creating emotionally memorable moments "
            "that viewers already care about."
        )

    else:

        strongest = (
            "Your biggest strength is making familiar ideas easy to understand "
            "and enjoyable to watch."
        )

    # Growth Opportunity

    if engagement_rate < 2:

        opportunity = (
            "Focus on creating stronger emotional openings. "
            "The first few seconds should immediately tell viewers why this moment matters."
        )

    elif engagement_rate < 5:

        opportunity = (
            "Your audience is responding. "
            "Experimenting with pacing and stronger story setup could unlock further growth."
        )

    else:

        opportunity = (
            "Your engagement is healthy. "
            "The next opportunity is expanding your content range while keeping your identity intact."
        )

    # Next Best Move

    next_move = (
        "Start your next upload with the most powerful moment first, "
        "then provide context afterwards. "
        "Give viewers a reason to stay immediately."
    )

    return {

        "current_momentum": momentum,

        "strongest_area": strongest,

        "growth_opportunity": opportunity,

        "next_best_move": next_move
    }