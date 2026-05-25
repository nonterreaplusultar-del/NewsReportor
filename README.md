# Personal Bilingual Brief

A serverless RSS bilingual digest system. It fetches RSS feeds, calls the DeepSeek API to generate Chinese-English bilingual digests, saves Markdown files, and pushes summaries via Telegram Bot. Runs locally or via GitHub Actions cron — no VPS required.

## Features

- Fetches RSS feeds across 7 categories (AI, Programming, Politics, China, Finance, Security, Ideas)
- Generates concise bilingual (Chinese + English) digests via DeepSeek
- Deduplicates items across runs
- Pushes digests to Telegram
- Scheduled 4x daily via GitHub Actions (Beijing time: 08:30, 12:30, 18:30, 22:30)
- Manual trigger via `workflow_dispatch`

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

# View the latest digest
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
2. Generates a bilingual digest via DeepSeek
3. Saves to `digests/YYYY-MM-DD-HHMM.md` and `digests/latest.md`
4. Pushes to Telegram
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
├── digests/                 # Generated Markdown digests
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
│   ├── digest_builder.py    # Prompt construction
│   ├── telegram_client.py   # Telegram Bot API client
│   └── utils.py             # Logging, hashing helpers
└── .github/workflows/digest.yml
```

## Security Notes

- **Never commit `.env`** — it's in `.gitignore`
- **Never commit API keys** — use GitHub Secrets for CI, `.env` for local dev
- The code masks API keys in log output (shows only first 4 and last 4 characters)
- All secrets are passed via environment variables at runtime
- Telegram messages do not include raw RSS content — only the curated digest

## License

MIT
