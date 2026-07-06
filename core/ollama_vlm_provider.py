import os


OLLAMA_URL_DEFAULT = "http://localhost:11434/api/chat"
OLLAMA_MODEL_DEFAULT = "llava:7b"


def _setting(name, default=""):
    return os.getenv(name, "").strip() or default


def _ollama_url():
    return _setting("OLLAMA_URL", OLLAMA_URL_DEFAULT)


def _ollama_model():
    return _setting("OLLAMA_VLM_MODEL", OLLAMA_MODEL_DEFAULT)


def _strip_data_url(frame_data_url):
    value = str(frame_data_url or "").strip()
    if "," in value and value.startswith("data:image"):
        return value.split(",", 1)[1]
    return value


def observe_with_ollama(prompt, frame_data_urls, timeout_seconds=20):
    provider = "ollama"
    if not frame_data_urls:
        return {
            "status": "unavailable",
            "content": "",
            "provider": provider,
            "warning": "Ollama VLM unavailable: no frames were provided.",
        }

    images = [
        image
        for image in (_strip_data_url(frame_data_url) for frame_data_url in frame_data_urls)
        if image
    ]
    if not images:
        return {
            "status": "unavailable",
            "content": "",
            "provider": provider,
            "warning": "Ollama VLM unavailable: frame images could not be encoded.",
        }

    try:
        import requests

        response = requests.post(
            _ollama_url(),
            json={
                "model": _ollama_model(),
                "stream": False,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": images,
                    }
                ],
            },
            timeout=timeout_seconds,
        )
        if response.status_code != 200:
            return {
                "status": "failed",
                "content": "",
                "provider": provider,
                "warning": (
                    f"Ollama VLM request failed with HTTP {response.status_code}: "
                    f"{response.text[:500]}"
                ),
            }

        data = response.json()
        content = data.get("message", {}).get("content", "")
        if not content:
            return {
                "status": "failed",
                "content": "",
                "provider": provider,
                "warning": "Ollama VLM returned an empty response.",
            }

        return {
            "status": "success",
            "content": content,
            "provider": provider,
            "warning": "",
        }
    except Exception as exc:
        return {
            "status": "failed",
            "content": "",
            "provider": provider,
            "warning": f"Ollama VLM request failed: {str(exc)}",
        }