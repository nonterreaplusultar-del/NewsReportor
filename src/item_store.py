import json
import logging
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def load_items(path: Path) -> dict[str, dict]:
    """Read items.jsonl and return a dict keyed by item id."""
    items: dict[str, dict] = {}
    if not path.exists():
        return items
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                item_id = item.get("id")
                if item_id:
                    items[item_id] = item
            except json.JSONDecodeError:
                logger.warning("Skipping malformed line in items.jsonl")
    return items


def save_items(path: Path, items: dict[str, dict]) -> None:
    """Write items.jsonl with deduplicated items, one JSON object per line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items.values():
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def merge_items(existing: dict[str, dict], new_items: list[dict]) -> dict[str, dict]:
    """Merge new items into the existing dict, skipping duplicates by id."""
    merged = dict(existing)
    added = 0
    for item in new_items:
        item_id = item.get("id")
        if not item_id:
            continue
        if item_id not in merged:
            merged[item_id] = item
            added += 1
    logger.info("Merged items: %d existing, %d new, %d total", len(existing), added, len(merged))
    return merged


def load_state(path: Path) -> dict:
    """Read state.json or return a default state if the file doesn't exist."""
    if not path.exists():
        logger.info("No state file found, using fresh state.")
        return {"summarized_item_ids": [], "last_digest_at": "", "last_digest_file": ""}
    with open(path, "r", encoding="utf-8") as f:
        state = json.load(f)
    logger.info("Loaded state: %d summarized item ids", len(state.get("summarized_item_ids", [])))
    return state


def save_state(path, state):
    import json
    import os
    import tempfile
    from pathlib import Path

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        prefix=f"{path.stem}_",
        suffix=path.suffix,
        dir=path.parent,
        text=True,
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            f.write("\n")

        # Windows 上 Path.rename() 不能稳定覆盖已有文件；
        # os.replace() 可以原子替换已有的 state.json。
        os.replace(tmp_path, path)

    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def get_unsummarized(
    items: dict[str, dict], state: dict, max_items: int
) -> list[dict]:
    """Return items not yet summarized, sorted by published date descending."""
    summarized_ids = set(state.get("summarized_item_ids", []))
    candidates = [item for item_id, item in items.items() if item_id not in summarized_ids]
    candidates.sort(key=lambda x: x.get("published", ""), reverse=True)
    logger.info(
        "Unsummarized candidates: %d (total items: %d, summarized: %d, limit: %d)",
        len(candidates), len(items), len(summarized_ids), max_items,
    )
    return candidates[:max_items]


def update_state(state: dict, new_ids: list[str], digest_file: str) -> dict:
    """Return updated state with new item ids appended and trimmed to 10000."""
    existing_ids = state.get("summarized_item_ids", [])
    combined = existing_ids + new_ids
    if len(combined) > 10000:
        combined = combined[-10000:]
    state["summarized_item_ids"] = combined
    state["last_digest_file"] = digest_file
    from datetime import datetime, timezone
    state["last_digest_at"] = datetime.now(timezone.utc).isoformat()
    return state
