import logging
import os
from pathlib import Path

from src.utils import safe_repr

logger = logging.getLogger(__name__)


def _load_dotenv_if_exists() -> None:
    """Try to load .env via python-dotenv. Silently skip if not installed or file missing."""
    try:
        import dotenv  # noqa: F401
    except ImportError:
        return
    env_path = Path(".env")
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except Exception:
            pass


def load_config() -> dict:
    """Load configuration from environment variables with sensible defaults."""
    _load_dotenv_if_exists()

    config = {
        "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "deepseek_base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        "deepseek_model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"),
        "deepseek_reasoning_effort": os.getenv("DEEPSEEK_REASONING_EFFORT", "high"),
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
        "max_items_per_digest": int(os.getenv("MAX_ITEMS_PER_DIGEST", "80")),
    }

    # Normalize model name: strip "[...]" suffix like "[1m]"
    model = config["deepseek_model"]
    if "[" in model:
        config["deepseek_model"] = model.split("[")[0]

    _log_config(config)
    return config


def _log_config(cfg: dict) -> None:
    logger.info("Configuration loaded:")
    logger.info("  DEEPSEEK_API_KEY       = %s", safe_repr(cfg["deepseek_api_key"]))
    logger.info("  DEEPSEEK_BASE_URL      = %s", cfg["deepseek_base_url"])
    logger.info("  DEEPSEEK_MODEL         = %s", cfg["deepseek_model"])
    logger.info("  DEEPSEEK_REASONING_EFFORT = %s", cfg["deepseek_reasoning_effort"])
    logger.info("  TELEGRAM_BOT_TOKEN     = %s", safe_repr(cfg["telegram_bot_token"]))
    logger.info("  TELEGRAM_CHAT_ID       = %s", safe_repr(cfg["telegram_chat_id"]))
    logger.info("  MAX_ITEMS_PER_DIGEST   = %d", cfg["max_items_per_digest"])


def validate_config(cfg: dict) -> None:
    """Raise ValueError if required config values are missing."""
    missing = []
    if not cfg["deepseek_api_key"]:
        missing.append("DEEPSEEK_API_KEY")
    if missing:
        raise ValueError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            "Set them in .env or export them before running."
        )
