"""
Stratify OpenAI Provider

Supports:
- Vision requests with images
- Text-only requests for content understanding
"""

import os
import requests


OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4.1-mini")
DEFAULT_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini")


def _post_openai(payload, timeout_seconds):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return {
            "status": "unavailable",
            "provider": "openai",
            "content": "",
            "warning": "OPENAI_API_KEY not configured.",
        }

    try:
        response = requests.post(
            OPENAI_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout_seconds,
        )

        if response.status_code != 200:
            return {
                "status": "failed",
                "provider": "openai",
                "content": "",
                "warning": f"HTTP {response.status_code}: {response.text[:500]}",
            }

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        return {
            "status": "success",
            "provider": "openai",
            "content": content,
            "warning": "",
        }

    except Exception as exc:
        return {
            "status": "failed",
            "provider": "openai",
            "content": "",
            "warning": str(exc),
        }


def observe_with_openai(prompt, frame_data_urls, timeout_seconds=30):
    content = [{"type": "text", "text": prompt}]

    for img in frame_data_urls or []:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": img},
            }
        )

    payload = {
        "model": DEFAULT_VISION_MODEL,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.1,
        "max_tokens": 700,
    }

    return _post_openai(payload, timeout_seconds)


def observe_text_with_openai(prompt, timeout_seconds=30):
    payload = {
        "model": DEFAULT_TEXT_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.1,
        "max_tokens": 700,
    }

    return _post_openai(payload, timeout_seconds)