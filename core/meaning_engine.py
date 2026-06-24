def generate_content_meaning(video, emotion, context):

    center = emotion.get("center", "emotional strength")

    return {
        "human_truth":
            f"People are drawn to {center} because it represents qualities they wish they had in difficult moments.",

        "core_desire":
            "Viewers are not only seeking entertainment. They want to experience emotions that make them feel stronger, smarter, or more confident.",

        "identity_viewers_admire":
            f"The audience admires people who embody {center} and remain emotionally powerful under pressure.",

        "emotional_fantasy":
            "The viewer imagines becoming the kind of person who can face challenges with confidence and control.",

        "why_this_matters":
            "This content matters because it satisfies an emotional need that goes beyond information. It gives viewers a feeling they want to experience again and again."
    }