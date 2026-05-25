import json
import logging
import textwrap

import requests

from src.utils import safe_repr

logger = logging.getLogger(__name__)


class DeepSeekError(Exception):
    """Raised when the DeepSeek API call fails."""


def generate_digest(
    messages: list[dict],
    api_key: str,
    base_url: str,
    model: str,
    reasoning_effort: str = "high",
    max_tokens: int = 6000,
    temperature: float = 0.3,
    timeout: int = 90,
) -> str:
    """Call the DeepSeek chat completions API and return the response content."""
    url = f"{base_url.rstrip('/')}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "thinking": {"type": "enabled"},
        "reasoning_effort": reasoning_effort,
    }

    logger.info("Calling DeepSeek API: model=%s, messages=%d, timeout=%ds",
                 model, len(messages), timeout)
    logger.info("API key: %s", safe_repr(api_key))

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.Timeout:
        raise DeepSeekError(f"DeepSeek API timed out after {timeout}s")
    except requests.RequestException as exc:
        raise DeepSeekError(f"DeepSeek API request failed: {exc}")

    if not resp.ok:
        body = resp.text[:500]
        raise DeepSeekError(
            f"DeepSeek API returned HTTP {resp.status_code}: {body}"
        )

    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        raise DeepSeekError(f"Failed to parse DeepSeek response JSON: {exc}")

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise DeepSeekError(
            f"Unexpected DeepSeek response structure: {json.dumps(data, ensure_ascii=False)[:500]}"
        )

    tokens_used = data.get("usage", {})
    logger.info(
        "DeepSeek response: %d chars, usage=%s",
        len(content) if content else 0,
        json.dumps(tokens_used, ensure_ascii=False) if tokens_used else "N/A",
    )

    if not content:
        raise DeepSeekError("DeepSeek returned empty content")

    return content
