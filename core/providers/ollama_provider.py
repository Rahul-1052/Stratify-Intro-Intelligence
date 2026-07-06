"""
Stratify Ollama Provider

Supports:
- Vision requests with images
- Text-only requests for content understanding
"""

import os
import requests


DEFAULT_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava:7b")
DEFAULT_TEXT_MODEL = os.getenv("OLLAMA_TEXT_MODEL", "qwen2.5-coder:7b")
DEFAULT_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")


def _extract_image(data_url):
    if not data_url:
        return ""

    value = str(data_url).strip()

    if "," in value:
        return value.split(",", 1)[1]

    return value


def _post_ollama(payload, timeout_seconds):
    try:
        response = requests.post(
            DEFAULT_URL,
            json=payload,
            timeout=timeout_seconds,
        )

    except requests.exceptions.ConnectionError:
        return {
            "status": "unavailable",
            "provider": "ollama",
            "content": "",
            "warning": "Local Ollama server is not running.",
        }

    except requests.exceptions.Timeout:
        return {
            "status": "failed",
            "provider": "ollama",
            "content": "",
            "warning": "Ollama timed out.",
        }

    except Exception as exc:
        return {
            "status": "failed",
            "provider": "ollama",
            "content": "",
            "warning": str(exc),
        }

    if response.status_code != 200:
        return {
            "status": "failed",
            "provider": "ollama",
            "content": "",
            "warning": f"HTTP {response.status_code}: {response.text[:500]}",
        }

    try:
        data = response.json()
    except Exception:
        return {
            "status": "failed",
            "provider": "ollama",
            "content": "",
            "warning": "Ollama returned invalid JSON.",
        }

    content = data.get("message", {}).get("content", "").strip()

    if not content:
        return {
            "status": "failed",
            "provider": "ollama",
            "content": "",
            "warning": "Ollama returned an empty response.",
        }

    return {
        "status": "success",
        "provider": "ollama",
        "content": content,
        "warning": "",
    }


def observe_with_ollama(prompt, frame_data_urls, timeout_seconds=60):
    if not frame_data_urls:
        return {
            "status": "unavailable",
            "provider": "ollama",
            "content": "",
            "warning": "No frames supplied for Ollama vision request.",
        }

    images = [
        _extract_image(img)
        for img in frame_data_urls
        if _extract_image(img)
    ]

    if not images:
        return {
            "status": "unavailable",
            "provider": "ollama",
            "content": "",
            "warning": "No valid images supplied for Ollama vision request.",
        }

    payload = {
        "model": DEFAULT_VISION_MODEL,
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": images,
            }
        ],
        "options": {
            "temperature": 0.1,
            "num_ctx": 8192,
        },
    }

    return _post_ollama(payload, timeout_seconds)


def observe_text_with_ollama(prompt, timeout_seconds=30):
    payload = {
        "model": DEFAULT_TEXT_MODEL,
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "options": {
            "temperature": 0.1,
            "num_ctx": 8192,
        },
    }

    return _post_ollama(payload, timeout_seconds)