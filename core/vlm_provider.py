import os

from core.ollama_vlm_provider import observe_with_ollama


OPENAI_URL = "https://api.openai.com/v1/chat/completions"
NVIDIA_URL_DEFAULT = "https://integrate.api.nvidia.com/v1/chat/completions"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
NVIDIA_DEFAULT_MODEL = "nvidia/llama-3.2-11b-vision-instruct"


def _streamlit_secret(name, default=""):
    try:
        import streamlit as st

        return st.secrets.get(name, default)
    except Exception:
        return default


def _setting(name, default=""):
    return os.getenv(name, "").strip() or str(_streamlit_secret(name, default)).strip()


def _openai_key():
    return _setting("OPENAI_API_KEY")


def _nvidia_key():
    return _setting("NVIDIA_API_KEY")


def _openai_model():
    return (
        _setting("OPENAI_VISION_MODEL")
        or _setting("OPENAI_MODEL")
        or OPENAI_DEFAULT_MODEL
    )


def _nvidia_model():
    return (
        _setting("NVIDIA_VLM_MODEL")
        or _setting("STRATIFY_VLM_MODEL")
        or NVIDIA_DEFAULT_MODEL
    )


def _nvidia_url():
    return _setting("NVIDIA_URL") or NVIDIA_URL_DEFAULT


def _content(prompt, frame_data_urls):
    return [
        {"type": "text", "text": prompt},
        *[
            {
                "type": "image_url",
                "image_url": {"url": frame_data_url},
            }
            for frame_data_url in frame_data_urls
        ],
    ]


def _post_chat_completion(url, key, payload, timeout_seconds):
    try:
        import requests

        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout_seconds,
        )
        if response.status_code != 200:
            response_text = response.text[:500] if response.text else ""
            return {
                "status": "failed",
                "content": "",
                "provider": "",
                "warning": (
                    f"VLM request failed with HTTP {response.status_code}: "
                    f"{response_text}"
                ),
            }

        data = response.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return {
            "status": "success",
            "content": content,
            "provider": "",
            "warning": "",
        }
    except Exception as exc:
        return {
            "status": "failed",
            "content": "",
            "provider": "",
            "warning": f"VLM request failed: {str(exc)}",
        }


def _with_warning(result, provider, warnings):
    result["provider"] = provider
    result["warnings"] = warnings + (
        [result["warning"]] if result.get("warning") else []
    )
    return result


def _unavailable(provider, warnings):
    return {
        "status": "unavailable",
        "content": "",
        "provider": provider,
        "warning": warnings[-1] if warnings else "VLM observation is unavailable.",
        "warnings": warnings,
    }


def observe_with_vlm(prompt, frame_data_urls, timeout_seconds=20):
    if not frame_data_urls:
        return {
            "status": "unavailable",
            "content": "",
            "provider": "",
            "warning": "No frames were available for VLM observation.",
            "warnings": ["No frames were available for VLM observation."],
        }

    warnings = ["Trying Ollama local VLM provider first."]
    ollama_result = observe_with_ollama(
        prompt,
        frame_data_urls,
        timeout_seconds=timeout_seconds,
    )
    if ollama_result.get("status") == "success":
        ollama_result["warnings"] = warnings + ["Ollama local VLM provider succeeded."]
        return ollama_result
    if ollama_result.get("warning"):
        warnings.append(ollama_result["warning"])

    openai_key = _openai_key()
    if openai_key:
        warnings.append("Trying OpenAI vision fallback because OPENAI_API_KEY is configured.")
        result = _post_chat_completion(
            OPENAI_URL,
            openai_key,
            {
                "model": _openai_model(),
                "temperature": 0.1,
                "max_tokens": 700,
                "messages": [
                    {
                        "role": "user",
                        "content": _content(prompt, frame_data_urls),
                    }
                ],
            },
            timeout_seconds,
        )
        if result.get("status") == "success":
            return _with_warning(result, "openai", warnings)
        if result.get("warning"):
            warnings.append(f"OpenAI vision fallback failed: {result['warning']}")
    else:
        warnings.append("Skipping OpenAI vision fallback: OPENAI_API_KEY is not configured.")

    nvidia_key = _nvidia_key()
    if nvidia_key:
        warnings.append("Trying NVIDIA NIM fallback because NVIDIA_API_KEY is configured.")
        result = _post_chat_completion(
            _nvidia_url(),
            nvidia_key,
            {
                "model": _nvidia_model(),
                "temperature": 0.1,
                "max_tokens": 700,
                "messages": [
                    {
                        "role": "user",
                        "content": _content(prompt, frame_data_urls),
                    }
                ],
            },
            timeout_seconds,
        )
        if result.get("status") == "success":
            return _with_warning(result, "nvidia", warnings)
        if result.get("warning"):
            warnings.append(f"NVIDIA NIM fallback failed: {result['warning']}")
    else:
        warnings.append("Skipping NVIDIA NIM fallback: NVIDIA_API_KEY is not configured.")

    return _unavailable(ollama_result.get("provider", "ollama"), warnings)