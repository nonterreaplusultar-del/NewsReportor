import logging
import re

import requests

from src.utils import normalize_telegram_html, safe_repr, strip_html_tags

logger = logging.getLogger(__name__)

# Max chars per Telegram message.  We stay well under the 4096 limit
# so that HTML entity expansion and multi-byte chars have headroom.
MAX_MSG_LEN = 3500

# Separator used between topic blocks (matches digest_builder.SEP).
_TOPIC_SEP_RE = re.compile(r"\n?(━{10,}|_{10,})\n?")


class TelegramError(Exception):
    """Raised when a Telegram API call fails."""


# ── splitting ──────────────────────────────────────────────────────


def _split_digest(text: str, max_len: int = MAX_MSG_LEN) -> list[str]:
    """Split digest text at topic-separator boundaries.

    Tries hard to keep each topic block intact.  If a single block
    still exceeds max_len it falls back to paragraph splitting.
    """
    # 1. Split on the ━━━━ separator lines between topics
    blocks = _TOPIC_SEP_RE.split(text)
    chunks: list[str] = []
    current = ""

    for block in blocks:
        if not block.strip():
            continue

        # A separator line gets appended to the *previous* chunk as a
        # visual footer, and the next topic starts fresh.
        if _TOPIC_SEP_RE.fullmatch(block):
            if current:
                current = current.rstrip() + "\n" + block
            continue

        # If adding this block fits, do it.
        if not current:
            current = block
        elif len(current) + len(block) + 2 <= max_len:
            current = current.rstrip() + "\n\n" + block
        else:
            # Start a new chunk.
            if current.strip():
                chunks.append(current.strip())
            current = block

    if current.strip():
        chunks.append(current.strip())

    # 2. For any chunk still over max_len, fall back to paragraph split.
    final_chunks: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_len:
            final_chunks.append(chunk)
        else:
            final_chunks.extend(_split_by_paragraphs(chunk, max_len))

    return final_chunks


def _split_by_paragraphs(text: str, max_len: int) -> list[str]:
    """Split text at blank-line paragraph boundaries."""
    paragraphs = re.split(r"\n\n+", text)
    result: list[str] = []
    current = ""
    for para in paragraphs:
        if current and len(current) + len(para) + 2 > max_len:
            result.append(current.strip())
            current = para
        else:
            current = current + ("\n\n" if current else "") + para
    if current.strip():
        result.append(current.strip())
    return result


# ── sending ────────────────────────────────────────────────────────


def send_message(
    text: str,
    bot_token: str,
    chat_id: str,
    parse_mode: str = "HTML",
    timeout: int = 30,
) -> requests.Response:
    """Send a single message via Telegram Bot API.  Returns the response object."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=timeout)
    return resp


def _send_with_fallback(
    text: str,
    bot_token: str,
    chat_id: str,
    timeout: int = 30,
) -> None:
    """Try sending with HTML parse_mode.  On failure, strip tags and retry as plain text."""
    # 1. Normalize
    html = normalize_telegram_html(text)

    # 2. Attempt HTML
    try:
        resp = send_message(html, bot_token, chat_id, parse_mode="HTML", timeout=timeout)
    except requests.Timeout:
        raise TelegramError("Telegram API timed out")
    except requests.RequestException as exc:
        raise TelegramError(f"Telegram API request failed: {exc}")

    if resp.ok:
        data = resp.json()
        if data.get("ok"):
            logger.info(
                "Telegram HTML sent (message_id=%s)",
                data.get("result", {}).get("message_id"),
            )
            return
        # ok==False but HTTP 200 — rare but handle
        err_desc = data.get("description", "unknown")
        logger.warning("Telegram HTML returned ok=false: %s", err_desc)
    else:
        logger.warning("Telegram HTML HTTP %d: %s", resp.status_code, resp.text[:300])

    # 3. Fallback: strip HTML and send as plain text
    logger.info("Falling back to plain text (no parse_mode)")
    plain = strip_html_tags(html)
    try:
        resp = send_message(plain, bot_token, chat_id, parse_mode="", timeout=timeout)
    except requests.Timeout:
        raise TelegramError("Telegram API timed out (fallback)")
    except requests.RequestException as exc:
        raise TelegramError(f"Telegram API request failed (fallback): {exc}")

    if not resp.ok:
        raise TelegramError(
            f"Telegram fallback also failed: HTTP {resp.status_code}: {resp.text[:300]}"
        )
    data = resp.json()
    if not data.get("ok"):
        raise TelegramError(
            f"Telegram fallback error: {data.get('description', 'unknown')}"
        )
    logger.info(
        "Telegram plain-text sent (message_id=%s)",
        data.get("result", {}).get("message_id"),
    )


# ── public API ─────────────────────────────────────────────────────


def send_digest(digest_text: str, bot_token: str, chat_id: str) -> None:
    """Send the full digest to Telegram via HTML parse_mode.

    Splits into multiple messages if needed (max 3500 chars each).
    If HTML send fails for any chunk, automatically strips tags and
    retries as plain text.
    """
    if not bot_token or not chat_id:
        raise TelegramError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")

    chunks = _split_digest(digest_text, MAX_MSG_LEN)
    total = len(chunks)

    logger.info(
        "Sending digest: %d chars in %d part(s) to chat %s",
        len(digest_text),
        total,
        safe_repr(chat_id),
    )

    for i, chunk in enumerate(chunks, 1):
        if total > 1:
            chunk = f"<b>Part {i}/{total}</b>\n━━━━━━━━━━━━━━\n\n{chunk}"
        _send_with_fallback(chunk, bot_token, chat_id)
