import hashlib
import logging
import sys


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
