#!/usr/bin/env python3
"""Main entry point: fetch RSS, generate bilingual digest, push via Telegram."""

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure the project root is on sys.path so `src.*` imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_config, validate_config
from src.digest_builder import build_prompt
from src.item_store import (
    get_unsummarized,
    load_items,
    load_state,
    merge_items,
    save_items,
    save_state,
    update_state,
)
from src.llm_client import DeepSeekError, generate_digest
from src.rss_fetcher import fetch_all, load_feeds
from src.telegram_client import TelegramError, send_digest
from src.utils import normalize_telegram_html, setup_logging

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RSS Bilingual Digest — run once")
    parser.add_argument("--no-telegram", action="store_true", help="Skip Telegram push")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and show candidates only, no LLM call")
    parser.add_argument("--limit", type=int, default=None, help="Max items to process (overrides env var)")
    parser.add_argument("--force", action="store_true", help="Ignore state, re-summarize recent items")
    return parser.parse_args()


def save_digest(text: str, digests_dir: Path) -> tuple[Path, Path]:
    """Save the digest to a timestamped file and update latest.md."""
    digests_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M")
    filename = f"{ts}.md"
    filepath = digests_dir / filename
    latest_path = digests_dir / "latest.md"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)
    logger.info("Saved digest: %s (%d chars)", filepath, len(text))

    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(text)
    logger.info("Updated latest.md")

    return filepath, latest_path


def main() -> None:
    setup_logging()
    args = parse_args()

    # 1. Load config (validate only when we actually need the API)
    cfg = load_config()
    if not args.dry_run:
        validate_config(cfg)

    max_items = args.limit if args.limit is not None else cfg["max_items_per_digest"]

    # 2. Load feeds
    feeds_path = ROOT / "config" / "feeds.yml"
    if not feeds_path.exists():
        logger.error("feeds.yml not found at %s", feeds_path)
        sys.exit(1)
    feeds = load_feeds(feeds_path)

    # 3. Fetch RSS
    new_items = fetch_all(feeds)
    if not new_items:
        logger.warning("No items fetched from any feed. Exiting.")
        return

    # 4. Merge into items.jsonl
    items_path = ROOT / "data" / "items.jsonl"
    existing = load_items(items_path)
    merged = merge_items(existing, new_items)
    save_items(items_path, merged)

    # 5. Load state
    state_path = ROOT / "data" / "state.json"
    state = load_state(state_path)

    # 6. Select candidates
    if args.force:
        logger.info("--force: ignoring summarized state, re-selecting recent %d items", max_items)
        all_items = sorted(merged.values(), key=lambda x: x.get("published", ""), reverse=True)
        candidates = all_items[:max_items]
    else:
        candidates = get_unsummarized(merged, state, max_items)

    # 7. Dry run
    if args.dry_run:
        logger.info("=== DRY RUN: %d candidate(s) ===", len(candidates))
        for idx, item in enumerate(candidates, 1):
            logger.info(
                "%d. [%s] %s (%s)",
                idx, item.get("source", "?"), item.get("title", ""), item.get("published", ""),
            )
        return

    # 8. No new content
    if not candidates:
        logger.info("No new items to summarize.")
        no_new_msg = (
            "🌐 <b>Personal Brief</b>\n"
            "<code>No new items</code>\n\n"
            "There are no unsummarized RSS items at this time. "
            "Check back at the next scheduled run."
        )
        if not args.no_telegram and cfg["telegram_bot_token"] and cfg["telegram_chat_id"]:
            try:
                send_digest(no_new_msg, cfg["telegram_bot_token"], cfg["telegram_chat_id"])
            except TelegramError as exc:
                logger.error("Telegram push failed: %s", exc)
        return

    logger.info("Selected %d items for summarization", len(candidates))

    # 9. Call DeepSeek
    messages = build_prompt(candidates)
    try:
        digest_text = generate_digest(
            messages=messages,
            api_key=cfg["deepseek_api_key"],
            base_url=cfg["deepseek_base_url"],
            model=cfg["deepseek_model"],
            reasoning_effort=cfg["deepseek_reasoning_effort"],
        )
    except DeepSeekError as exc:
        logger.error("DeepSeek API call failed: %s", exc)
        logger.error("State NOT updated — items will be retried next run.")
        sys.exit(1)

    # 10. Normalize and save digest
    digest_text = normalize_telegram_html(digest_text)
    digests_dir = ROOT / "digests"
    digest_path, _ = save_digest(digest_text, digests_dir)

    # 11. Telegram push
    if not args.no_telegram and cfg["telegram_bot_token"] and cfg["telegram_chat_id"]:
        try:
            send_digest(digest_text, cfg["telegram_bot_token"], cfg["telegram_chat_id"])
        except TelegramError as exc:
            logger.error("Telegram push failed: %s", exc)
    elif args.no_telegram:
        logger.info("Telegram push skipped (--no-telegram)")

    # 12. Update state
    new_ids = [item["id"] for item in candidates if item.get("id")]
    update_state(state, new_ids, digest_path.name)
    save_state(state_path, state)
    logger.info("State updated: %d items summarized", len(new_ids))
    logger.info("Done.")


if __name__ == "__main__":
    main()
