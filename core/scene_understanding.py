def understand_scene(vision):
    emotion = vision.get("emotion", "")
    visual_tone = vision.get("visual_tone", "")
    story_setup = vision.get("story_setup", "")
    energy = vision.get("energy", "")

    what_is_happening = (
        f"The intro appears to build around {story_setup.lower()} "
        f"with a feeling of {emotion.lower()}."
    )

    main_subject = (
        "The main subject is the emotional focus of the opening, not just what appears on screen."
    )

    scene_type = (
        "The scene is built to create immediate emotional context."
    )

    visual_style = (
        f"The visual style feels {visual_tone.lower()}."
    )

    emotional_direction = (
        f"The opening is moving toward {energy.lower()}."
    )

    return {
        "what_is_happening": what_is_happening,
        "main_subject": main_subject,
        "scene_type": scene_type,
        "visual_style": visual_style,
        "emotional_direction": emotional_direction,
    }