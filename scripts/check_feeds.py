#!/usr/bin/env python3
"""Check all configured RSS feeds and report their status."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rss_fetcher import fetch_feed, load_feeds
from src.utils import setup_logging

setup_logging()

ROOT = Path(__file__).resolve().parent.parent
feeds_path = ROOT / "config" / "feeds.yml"

if not feeds_path.exists():
    print(f"ERROR: feeds.yml not found at {feeds_path}")
    sys.exit(1)

feeds = load_feeds(feeds_path)
print(f"\nChecking {len(feeds)} feeds...\n")
print(f"{'Status':<6} {'Items':<6} {'Category':<20} Name")
print("-" * 80)

ok_count = 0
fail_count = 0

for feed in feeds:
    name = feed.get("name", "?")
    category = feed.get("category", "?")
    try:
        items = fetch_feed(feed)
        if items:
            print(f"  OK    {len(items):<6} {category:<20} {name}")
            ok_count += 1
        else:
            print(f"  EMPTY {0:<6} {category:<20} {name}")
            ok_count += 1
    except Exception as exc:
        print(f"  FAIL  {0:<6} {category:<20} {name}  ({exc})")
        fail_count += 1
    time.sleep(0.3)  # Be polite to servers

print("-" * 80)
print(f"\nOK: {ok_count}, FAIL: {fail_count}")
