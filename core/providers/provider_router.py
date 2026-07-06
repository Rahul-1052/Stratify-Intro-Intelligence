"""
Stratify AI Router

Routes AI requests by capability:

1. observe_visual(...)
   - Prompt + images
   - Used by Visual Observer

2. observe_text(...)
   - Prompt only
   - Used by Content Understanding

Provider priority:
Ollama → OpenAI → NVIDIA → graceful fallback
"""

from core.providers.ollama_provider import observe_with_ollama, observe_text_with_ollama
from core.providers.openai_provider import observe_with_openai, observe_text_with_openai
from core.providers.nvidia_provider import observe_with_nvidia, observe_text_with_nvidia


def observe_visual(prompt, frame_data_urls, timeout_seconds=30):
    if not frame_data_urls:
        return {
            "status": "unavailable",
            "provider": "",
            "content": "",
            "warning": "No frames were available for visual AI request.",
            "warnings": ["No frames were available for visual AI request."],
        }

    warnings = []

    for provider_name, fn in [
        ("Ollama", observe_with_ollama),
        ("OpenAI", observe_with_openai),
        ("NVIDIA", observe_with_nvidia),
    ]:
        result = fn(
            prompt=prompt,
            frame_data_urls=frame_data_urls,
            timeout_seconds=timeout_seconds,
        )

        if result.get("status") == "success":
            return {**result, "warnings": warnings}

        if result.get("warning"):
            warnings.append(f"{provider_name}: {result['warning']}")

    return {
        "status": "unavailable",
        "provider": "",
        "content": "",
        "warning": warnings[-1] if warnings else "No visual AI provider was available.",
        "warnings": warnings or ["No visual AI provider was available."],
    }


def observe_text(prompt, timeout_seconds=30):
    if not prompt:
        return {
            "status": "unavailable",
            "provider": "",
            "content": "",
            "warning": "No prompt was supplied for text AI request.",
            "warnings": ["No prompt was supplied for text AI request."],
        }

    warnings = []

    for provider_name, fn in [
        ("Ollama", observe_text_with_ollama),
        ("OpenAI", observe_text_with_openai),
        ("NVIDIA", observe_text_with_nvidia),
    ]:
        result = fn(
            prompt=prompt,
            timeout_seconds=timeout_seconds,
        )

        if result.get("status") == "success":
            return {**result, "warnings": warnings}

        if result.get("warning"):
            warnings.append(f"{provider_name}: {result['warning']}")

    return {
        "status": "unavailable",
        "provider": "",
        "content": "",
        "warning": warnings[-1] if warnings else "No text AI provider was available.",
        "warnings": warnings or ["No text AI provider was available."],
    }


# Backward compatibility for visual_observer.py
def observe_with_provider(prompt, frame_data_urls=None, timeout_seconds=30):
    if frame_data_urls:
        return observe_visual(
            prompt=prompt,
            frame_data_urls=frame_data_urls,
            timeout_seconds=timeout_seconds,
        )

    return observe_text(
        prompt=prompt,
        timeout_seconds=timeout_seconds,
    )