import logging
import re

import requests

from src.utils import safe_repr

logger = logging.getLogger(__name__)

MAX_MSG_LEN = 3800


class TelegramError(Exception):
    """Raised when a Telegram API call fails."""


def _split_by_paragraphs(text: str, max_len: int = MAX_MSG_LEN) -> list[str]:
    """Split text at blank-line paragraph boundaries, keeping each chunk <= max_len."""
    paragraphs = re.split(r"\n\n+", text)
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if current and len(current) + len(para) + 2 > max_len:
            chunks.append(current.strip())
            current = para
        else:
            current = current + ("\n\n" if current else "") + para
    if current.strip():
        chunks.append(current.strip())
    return chunks


def send_message(
    text: str,
    bot_token: str,
    chat_id: str,
    timeout: int = 30,
) -> None:
    """Send a single Telegram message via Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except requests.Timeout:
        raise TelegramError("Telegram API timed out")
    except requests.RequestException as exc:
        raise TelegramError(f"Telegram API request failed: {exc}")

    if not resp.ok:
        body = resp.text[:500]
        raise TelegramError(f"Telegram API HTTP {resp.status_code}: {body}")

    data = resp.json()
    if not data.get("ok"):
        raise TelegramError(f"Telegram API error: {data.get('description', 'unknown')}")
    logger.info("Telegram message sent (message_id=%s)", data.get("result", {}).get("message_id"))


def send_digest(digest_text: str, bot_token: str, chat_id: str) -> None:
    """Send the full digest, splitting into multiple messages if needed."""
    if not bot_token or not chat_id:
        raise TelegramError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")

    chunks = _split_by_paragraphs(digest_text, MAX_MSG_LEN)
    total = len(chunks)

    logger.info("Sending digest: %d chars in %d part(s) to chat %s",
                 len(digest_text), total, safe_repr(chat_id))

    for i, chunk in enumerate(chunks, 1):
        if total > 1:
            chunk = f"Part {i}/{total}\n\n{chunk}"
        send_message(chunk, bot_token, chat_id)
