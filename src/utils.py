import hashlib
import logging
import re
import sys

# Tags Telegram HTML parse_mode supports.
# We keep: <b> <i> <a href="..."> <code> <pre>
# Everything else gets stripped (tags removed, inner text kept).
_ALLOWED_TAGS = {"b", "i", "a", "code", "pre"}

# Match any opening or closing HTML tag.
_TAG_RE = re.compile(r"</?(\w+)[^>]*>")

# Match backtick code fences that DeepSeek might emit despite instructions.
_FENCE_RE = re.compile(r"^```\w*\n?", re.MULTILINE)


def sha256(text: str) -> str:
    """Generate a stable SHA-256 hex digest for the given text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_repr(key: str) -> str:
    """Mask an API key so only the first 4 and last 4 characters are shown."""
    if not key or len(key) < 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with a sensible format."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )


def strip_html_tags(text: str) -> str:
    """Remove ALL HTML tags, returning plain text. Used for Telegram fallback."""
    if not text:
        return ""
    # Remove code fences first
    text = _FENCE_RE.sub("", text)
    # Replace <br> variants with newlines before stripping
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    # Strip all tags
    text = _TAG_RE.sub("", text)
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_telegram_html(text: str) -> str:
    """Sanitize HTML for Telegram's HTML parse_mode.

    - Strips code fences (```html, ```)
    - Strips unsupported tags (<h1>, <ul>, <li>, <div>, <span>, <br>, etc.)
      while preserving inner text
    - Keeps: <b>, <i>, <a href="...">, <code>, <pre>
    - Normalizes line endings
    - Returns clean, safe HTML
    """
    if not text:
        return ""

    # 1. Remove ``` fences DeepSeek may emit
    text = _FENCE_RE.sub("", text)
    # Also trailing ```
    text = re.sub(r"\n?```\s*$", "", text)

    # 2. Replace <br> variants with newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

    # 3. Strip unsupported tags but keep inner text.
    #    Supported: b, i, a, code, pre (and their closing tags).
    def _filter_tag(m: re.Match) -> str:
        tag = m.group(1).lower()
        if tag in _ALLOWED_TAGS:
            return m.group(0)  # keep as-is
        return ""  # strip unsupported tag, keep inner text

    text = _TAG_RE.sub(_filter_tag, text)

    # 4. Normalize line endings (Windows CRLF -> LF)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 5. Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
