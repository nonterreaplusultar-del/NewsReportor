#!/usr/bin/env python3
"""Preview recent items from the local item store."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.item_store import load_items
from src.utils import setup_logging

setup_logging()

parser = argparse.ArgumentParser(description="Preview stored RSS items")
parser.add_argument("--limit", type=int, default=20, help="Number of items to show (default: 20)")
args = parser.parse_args()

ROOT = Path(__file__).resolve().parent.parent
items_path = ROOT / "data" / "items.jsonl"

items = load_items(items_path)
sorted_items = sorted(items.values(), key=lambda x: x.get("published", ""), reverse=True)

print(f"\nTotal items in store: {len(items)}")
print(f"Showing most recent {min(args.limit, len(sorted_items))}:\n")

for idx, item in enumerate(sorted_items[: args.limit], 1):
    print(f"{idx}. [{item.get('category', '?')}] {item.get('title', '')}")
    print(f"   Source: {item.get('source', '')}")
    print(f"   Published: {item.get('published', '')}")
    if item.get("link"):
        print(f"   Link: {item.get('link', '')}")
    summary = item.get("summary", "")
    if summary:
        print(f"   Summary: {summary[:200]}{'...' if len(summary) > 200 else ''}")
    print()
