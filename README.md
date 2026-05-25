# Personal Bilingual Brief

A serverless RSS bilingual digest system. It fetches RSS feeds, calls the DeepSeek API to generate Chinese-English bilingual digests, saves HTML-formatted briefs, and pushes summaries via Telegram Bot. Runs locally or via GitHub Actions cron — no VPS required.

## Features

- Fetches RSS feeds across 7 categories (AI, Programming, Politics, China, Finance, Security, Ideas)
- Generates concise bilingual (Chinese + English) digests via DeepSeek
- Outputs **Telegram-friendly HTML** — clean, readable, mobile-optimized
- Deduplicates items across runs
- Pushes digests to Telegram with HTML formatting
- Automatic fallback to plain text if HTML send fails
- Scheduled 4x daily via GitHub Actions (Beijing time: 08:30, 12:30, 18:30, 22:30)
- Manual trigger via `workflow_dispatch`

## Digest Format

The digest is generated as **Telegram-safe HTML** using only five tags:

| Tag | Usage |
|---|---|
| `<b>` | Bold titles, section headers |
| `<i>` | English subtitles |
| `<a href="...">` | Source links in "Worth Reading" |
| `<code>` | Timestamp |
| `<pre>` | Rare, for code-like content |

Lists use plain-text symbols (•, —, 1., 2.) — no `<ul>` or `<li>`.
Separators use `━━━━━━━━━━━━━━` — no `<hr>`.

The file extension is `.md` for compatibility, but the content is **HTML** optimized for Telegram's `parse_mode=HTML`.

### Why HTML, not MarkdownV2?

Telegram's MarkdownV2 requires strict escaping of special characters (`_`, `*`, `[`, `]`, `(`, `)`, etc.). News headlines frequently contain these characters, causing send failures. HTML parse_mode is more forgiving — we only use a safe subset of tags.

## Requirements

- Python 3.10+
- DeepSeek API key
- Telegram Bot Token (optional, for push notifications)

## Local Setup

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd personal-bilingual-brief

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and fill in your API keys
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DEEPSEEK_API_KEY` | Yes | — | DeepSeek API key |
| `DEEPSEEK_BASE_URL` | No | `https://api.deepseek.com` | API base URL |
| `DEEPSEEK_MODEL` | No | `deepseek-v4-pro` | Model name |
| `DEEPSEEK_REASONING_EFFORT` | No | `high` | Reasoning effort level |
| `TELEGRAM_BOT_TOKEN` | No | — | Telegram bot token (from @BotFather) |
| `TELEGRAM_CHAT_ID` | No | — | Target chat/channel ID |
| `MAX_ITEMS_PER_DIGEST` | No | `80` | Max items per digest run |

## Local Usage

```bash
# Check that all feeds are working
python scripts/check_feeds.py

# Preview stored items
python scripts/preview_items.py --limit 20

# Dry run: fetch feeds and show candidates without calling DeepSeek
python scripts/run_digest_once.py --dry-run --limit 10

# Generate digest without Telegram push
python scripts/run_digest_once.py --no-telegram --limit 20

# Full run with Telegram push
python scripts/run_digest_once.py

# Force re-summarize recent items (ignore state)
python scripts/run_digest_once.py --force --limit 15

# View the latest digest locally
cat digests/latest.md
```

## Test Commands

```bash
# 1. Compile check — verify all Python files are syntactically valid
python -m py_compile src/*.py scripts/*.py

# 2. Check feed configuration
python scripts/check_feeds.py

# 3. Dry run — fetch and display candidates
python scripts/run_digest_once.py --dry-run --limit 10

# 4. Generate digest locally (no Telegram)
python scripts/run_digest_once.py --no-telegram --limit 20
```

## Telegram Behavior

### Formatting

Messages are sent with `parse_mode=HTML` using only safe tags: `<b>`, `<i>`, `<a>`, `<code>`, `<pre>`.

### Message Splitting

- Each message is capped at **3500 characters** (well under Telegram's 4096 limit)
- Splitting happens at topic boundaries (━━━ separators) to avoid breaking mid-topic
- Multi-part messages are prefixed: `<b>Part 1/3</b>`

### Automatic Fallback

If HTML send fails for any reason (malformed tags, unexpected characters), the system automatically:
1. Strips all HTML tags
2. Retries as **plain text**
3. Logs the fallback for visibility

This means you'll always receive the digest — formatted if possible, plain text if not.

### Previewing the Digest Locally

The latest digest is saved to `digests/latest.md`. Although the file extension is `.md`, the content is Telegram-safe HTML. To preview:

```bash
cat digests/latest.md
```

Or open it in a browser as HTML to see the formatting.

## GitHub Actions Setup

### 1. Add Secrets

Go to your repository → **Settings** → **Secrets and variables** → **Actions** and add:

| Secret | Required | Description |
|---|---|---|
| `DEEPSEEK_API_KEY` | Yes | Your DeepSeek API key |
| `TELEGRAM_BOT_TOKEN` | Optional | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Optional | Telegram chat/channel ID |
| `DEEPSEEK_BASE_URL` | No | Override API base URL |
| `DEEPSEEK_MODEL` | No | Override model name |
| `DEEPSEEK_REASONING_EFFORT` | No | Override reasoning effort |

### 2. Workflow Triggers

- **Scheduled**: Runs 4 times daily at Beijing time 08:30, 12:30, 18:30, 22:30
- **Manual**: Go to Actions → "Bilingual RSS Digest" → "Run workflow"

### 3. What Happens

Each run:
1. Fetches RSS feeds
2. Generates a bilingual digest via DeepSeek (Telegram-safe HTML)
3. Saves to `digests/YYYY-MM-DD-HHMM.md` and `digests/latest.md`
4. Pushes to Telegram with HTML formatting (with plain-text fallback)
5. Commits updated state back to the repository

## Adding RSS Feeds

Edit `config/feeds.yml`:

```yaml
feeds:
  - name: "My Feed"
    category: "AI / Technology"
    url: "https://example.com/rss.xml"
    limit: 10  # optional, max items per fetch
```

Categories are free-form but these are used by default:
- AI / Technology
- Programming
- World Politics
- China
- Finance / Policy
- Security
- Literature / Ideas

## Project Structure

```
personal-bilingual-brief/
├── config/feeds.yml        # RSS source configuration
├── data/items.jsonl         # Persisted RSS items (one JSON per line)
├── data/state.json          # Summary state (which items have been processed)
├── digests/                 # Generated digests (HTML content, .md extension)
│   ├── YYYY-MM-DD-HHMM.md
│   └── latest.md
├── scripts/
│   ├── run_digest_once.py   # Main entry point
│   ├── check_feeds.py       # Feed health check
│   └── preview_items.py     # Browse stored items
├── src/                     # Core modules
│   ├── config.py            # Env var loading
│   ├── rss_fetcher.py       # RSS fetching via feedparser
│   ├── item_store.py        # JSONL + state persistence
│   ├── llm_client.py        # DeepSeek API client
│   ├── digest_builder.py    # Prompt construction (Telegram HTML)
│   ├── telegram_client.py   # Telegram Bot API (HTML + fallback)
│   └── utils.py             # Logging, hashing, HTML sanitization
└── .github/workflows/digest.yml
```

## Security Notes

- **Never commit `.env`** — it's in `.gitignore`
- **Never commit API keys** — use GitHub Secrets for CI, `.env` for local dev
- The code masks API keys in log output (shows only first 4 and last 4 characters)
- All secrets are passed via environment variables at runtime
- Telegram messages do not include raw RSS content — only the curated digest
- Telegram bot token is never printed in logs

## License

MIT
