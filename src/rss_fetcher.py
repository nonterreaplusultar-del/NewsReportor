import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import feedparser
import yaml

from src.utils import sha256

logger = logging.getLogger(__name__)

# Common HTML tag pattern for stripping from summaries
_HTML_RE = re.compile(r"<[^>]*>")


def load_feeds(path: Path) -> list[dict]:
    """Parse feeds.yml and return a list of feed configuration dicts."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    feeds = data.get("feeds", []) if isinstance(data, dict) else data
    logger.info("Loaded %d feeds from %s", len(feeds), path)
    return feeds


def _make_item_id(title: str, link: str, source: str, published: str) -> str:
    """Generate a stable unique ID for an RSS item."""
    if link:
        return sha256(link)
    if source and title:
        return sha256(f"{source}:{title}")
    return sha256(f"{source}:{title}:{published}")


def _strip_html(text: str) -> str:
    """Remove HTML tags from a string."""
    if not text:
        return ""
    return _HTML_RE.sub("", text).strip()


def _parse_time(parsed_entry) -> str:
    """Extract a normalized ISO timestamp from a feedparser entry."""
    from time import mktime
    if hasattr(parsed_entry, "published_parsed") and parsed_entry.published_parsed:
        try:
            dt = datetime.fromtimestamp(mktime(parsed_entry.published_parsed), tz=timezone.utc)
            return dt.isoformat()
        except Exception:
            pass
    return datetime.now(timezone.utc).isoformat()


def fetch_feed(feed_config: dict, timeout: int = 30) -> list[dict]:
    """Fetch a single RSS feed and return normalized item dicts."""
    url = feed_config.get("url", "")
    name = feed_config.get("name", url)
    category = feed_config.get("category", "Uncategorized")
    limit = feed_config.get("limit", 0)

    logger.info("Fetching [%s] %s", category, name)

    try:
        req = Request(url, headers={"User-Agent": "personal-bilingual-brief/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        parsed = feedparser.parse(raw)
    except URLError as exc:
        logger.error("Feed HTTP error [%s]: %s", name, exc)
        return []
    except Exception as exc:
        logger.error("Feed error [%s]: %s", name, exc)
        return []

    if parsed.bozo and not parsed.entries:
        logger.warning("Feed parse warning [%s]: %s", name, parsed.bozo_exception)
        return []

    items = []
    entries = parsed.entries[:limit] if limit > 0 else parsed.entries

    for entry in entries:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "") or ""
        summary = _strip_html(getattr(entry, "summary", "") or getattr(entry, "description", ""))
        published = _parse_time(entry)

        if not title:
            continue

        item = {
            "id": _make_item_id(title, link, name, published),
            "title": title,
            "link": link,
            "source": name,
            "category": category,
            "published": published,
            "summary": summary,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        items.append(item)

    logger.info("  -> %d items", len(items))
    return items


def fetch_all(feeds: list[dict], timeout: int = 30) -> list[dict]:
    """Fetch all configured feeds and return a flat list of item dicts."""
    all_items = []
    for feed_config in feeds:
        try:
            items = fetch_feed(feed_config, timeout=timeout)
            all_items.extend(items)
        except Exception as exc:
            logger.error("Unexpected error fetching [%s]: %s", feed_config.get("name", "?"), exc)
    logger.info("Total fetched: %d items from %d feeds", len(all_items), len(feeds))
    return all_items
