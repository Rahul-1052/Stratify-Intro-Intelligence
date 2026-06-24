def generate_big_insight(
        emotion,
        context,
        scene):

    center = emotion.get(
        "center",
        "clear emotional payoff"
    )

    audience_desire = emotion.get(
        "audience_desire",
        "a meaningful experience"
    )

    creator_advantage = emotion.get(
        "creator_advantage",
        "turning familiar ideas into emotional moments"
    )

    growth_direction = emotion.get(
        "growth_direction",
        "make the emotional promise appear earlier"
    )


    big_insight = f"""

Your audience is not simply watching for information.

They are watching for **{center}**.

The strongest moments in your content are the moments where viewers feel:

"{audience_desire}"

That emotional experience is your real advantage.

"""


    identity = f"""

You are not creating ordinary videos.

You are creating experiences centered around:

{center}

And your strength is:

{creator_advantage}

"""


    future_direction = f"""

As you grow,

focus less on explaining.

Focus more on making viewers FEEL.

Next step:

{growth_direction}

"""


    return {

        "big_insight": big_insight,

        "identity": identity,

        "future_direction": future_direction
    }