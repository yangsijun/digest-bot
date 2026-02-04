# News Digest Bot

Automated news aggregation and summarization bot that fetches tech news from multiple sources, generates British English summaries with Claude AI, and delivers them via Telegram twice daily.

## Features

- **Multi-Source Aggregation**: Fetches from Hacker News, GeekNews, GitHub Trending, and Product Hunt
- **AI Summarization**: Uses Claude CLI to generate British English summaries with vocabulary footnotes
- **Scheduled Delivery**: Automatic digests at 08:00 and 20:00 KST (10 items each)
- **Smart Deduplication**: Cross-source URL matching with related article links
- **Interactive Telegram Bot**: Commands for search, bookmarks, and settings
- **Inline Actions**: Detail view, Korean translation, bookmark, and related articles
- **Persistent Storage**: SQLite database with WAL mode for all articles and summaries
- **Production Ready**: systemd service with auto-restart and daily backups

## Installation

### Prerequisites

- Python 3.10 or higher
- Claude CLI installed and configured (`claude --version`)
- Linux server with systemd (for production deployment)
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Product Hunt API credentials (from [Product Hunt API](https://api.producthunt.com/v2/docs))

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd digest-bot
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Initialize the database**
   ```bash
   python -c "from src.db import init_db; init_db()"
   ```

5. **Test the bot manually**
   ```bash
   python -m src.main
   ```

### Production Deployment

For production deployment with systemd:

```bash
sudo ./install.sh
```

This will:
- Create a `digest-bot` system user
- Install the systemd service
- Set up daily database backups (03:00 daily)
- Enable auto-start on boot

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ Yes | - | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | ✅ Yes | - | Your Telegram chat ID (single user mode) |
| `PRODUCTHUNT_CLIENT_ID` | ✅ Yes | - | Product Hunt OAuth2 client ID |
| `PRODUCTHUNT_CLIENT_SECRET` | ✅ Yes | - | Product Hunt OAuth2 client secret |
| `DATABASE_PATH` | No | `digest.db` | SQLite database file path |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE` | No | `digest_bot.log` | Log file path |

### Getting Credentials

**Telegram Bot Token:**
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy the bot token

**Telegram Chat ID:**
1. Message your bot
2. Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Find your `chat.id` in the JSON response

**Product Hunt API:**
1. Visit [Product Hunt API Dashboard](https://api.producthunt.com/v2/oauth/applications)
2. Create a new application
3. Copy Client ID and Client Secret

## Usage

### Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and bot introduction |
| `/help` | Display help and available commands |
| `/digest` | Manually trigger a digest generation |
| `/search <keyword>` | Search past summaries by keyword |
| `/bookmarks` | View your saved bookmarks |
| `/settings` | View current schedule times |

### Inline Buttons

Each digest item includes interactive buttons:

- **📖 상세 보기** (Detail): Request detailed analysis
- **🇰🇷 한국어 번역** (Translate): Request Korean translation
- **🔖 북마크** (Bookmark): Save article for later
- **🔗 관련 글** (Related): View related articles from other sources

### Manual Operation

Run a one-time digest:
```bash
cd /opt/digest-bot
python -c "from src.scheduler import run_digest; import asyncio; asyncio.run(run_digest('manual'))"
```

Test individual fetchers:
```bash
python -c "
import asyncio
from src.fetchers import HNFetcher
fetcher = HNFetcher()
items = asyncio.run(fetcher.fetch(limit=5))
print(f'Fetched {len(items)} items')
"
```

## Deployment

### systemd Service

**Start the service:**
```bash
sudo systemctl start digest-bot
```

**Check status:**
```bash
sudo systemctl status digest-bot
```

**View logs:**
```bash
sudo journalctl -u digest-bot -f
```

**Restart the service:**
```bash
sudo systemctl restart digest-bot
```

**Stop the service:**
```bash
sudo systemctl stop digest-bot
```

### Monitoring

**Check recent digests:**
```bash
sqlite3 /opt/digest-bot/digest.db "SELECT COUNT(*) FROM summaries WHERE date(created_at) = date('now')"
```

**View application logs:**
```bash
tail -f /opt/digest-bot/digest_bot.log
```

**Check backup status:**
```bash
ls -lh /opt/digest-bot/backups/
```

## Troubleshooting

### Bot not responding

**Problem:** Telegram bot doesn't respond to commands

**Solutions:**
1. Verify bot token: `echo $TELEGRAM_BOT_TOKEN`
2. Check chat ID matches: `echo $TELEGRAM_CHAT_ID`
3. Test bot API: `curl https://api.telegram.org/bot<TOKEN>/getMe`
4. Check service logs: `journalctl -u digest-bot -n 50`

### Claude CLI not found

**Problem:** `claude: command not found` in logs

**Solutions:**
1. Install Claude CLI: Follow [official installation guide](https://docs.anthropic.com/claude/docs/cli)
2. Verify installation: `claude --version`
3. Check PATH in service file: Ensure `/usr/local/bin` is in PATH
4. Update service file if needed: `sudo systemctl daemon-reload && sudo systemctl restart digest-bot`

### Product Hunt API errors

**Problem:** `401 Unauthorized` or `403 Forbidden` from Product Hunt

**Solutions:**
1. Verify credentials in `.env` file
2. Test OAuth token: `python -c "from src.auth.producthunt import get_access_token; import asyncio; print(asyncio.run(get_access_token()))"`
3. Check API quota: Visit [Product Hunt Dashboard](https://api.producthunt.com/v2/oauth/applications)
4. Regenerate credentials if expired

### Database locked

**Problem:** `database is locked` error

**Solutions:**
1. Check for concurrent processes: `ps aux | grep digest-bot`
2. Verify lock file: `ls -l /tmp/digest_bot.lock`
3. Remove stale lock: `rm /tmp/digest_bot.lock` (only if no process running)
4. Restart service: `sudo systemctl restart digest-bot`

### Service won't start

**Problem:** `systemctl start digest-bot` fails

**Solutions:**
1. Check service status: `systemctl status digest-bot`
2. View detailed logs: `journalctl -u digest-bot -xe`
3. Verify .env file exists: `ls -l /opt/digest-bot/.env`
4. Check file permissions: `ls -l /opt/digest-bot/`
5. Validate Python syntax: `python -m py_compile src/main.py`

### No digests received

**Problem:** Scheduled digests not arriving

**Solutions:**
1. Check scheduler is running: `journalctl -u digest-bot | grep "Scheduler started"`
2. Verify schedule times: `sqlite3 digest.db "SELECT * FROM settings WHERE key LIKE '%time'"`
3. Check timezone: Ensure server timezone is correct (`timedatectl`)
4. Test manual digest: `python -c "from src.scheduler import run_digest; import asyncio; asyncio.run(run_digest('test'))"`
5. Check for errors: `journalctl -u digest-bot --since "08:00" --until "08:30"`

## Architecture

### Project Structure

```
digest-bot/
├── src/
│   ├── main.py              # Entry point with scheduler initialization
│   ├── config.py            # Configuration and logging setup
│   ├── db.py                # SQLite database operations (WAL mode)
│   ├── scheduler.py         # APScheduler with digest pipeline
│   ├── summarizer.py        # Claude CLI wrapper for summarization
│   ├── dedup.py             # URL deduplication logic
│   ├── search.py            # Keyword search functionality
│   ├── settings.py          # Schedule settings management
│   ├── auth/
│   │   └── producthunt.py   # OAuth2 token management
│   ├── fetchers/
│   │   ├── base_fetcher.py  # Abstract base class with retry logic
│   │   ├── hn_fetcher.py    # Hacker News (Firebase API)
│   │   ├── geeknews_fetcher.py # GeekNews (RSS feed)
│   │   ├── github_fetcher.py   # GitHub Trending (API + scraping)
│   │   └── producthunt_fetcher.py # Product Hunt (GraphQL)
│   └── bot/
│       ├── bot.py           # Telegram bot with command handlers
│       ├── handlers.py      # Callback handlers and bookmark logic
│       ├── keyboards.py     # Inline keyboard layouts
│       └── utils.py         # Message splitting utility
├── tests/
│   ├── test_handlers.py     # Unit tests for bot handlers
│   └── test_integration.py  # Integration tests for full pipeline
├── cron/
│   └── backup.sh            # Daily SQLite backup script
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables template
├── digest-bot.service       # systemd service unit file
└── install.sh               # Production installation script
```

### Data Flow

1. **Fetch**: APScheduler triggers at 08:00 and 20:00 KST
2. **Aggregate**: Fetch 10 items from each source (HN, GeekNews, GitHub, Product Hunt)
3. **Deduplicate**: Remove cross-source duplicates, link related articles
4. **Summarize**: Generate British English summaries with Claude CLI
5. **Store**: Save articles and summaries to SQLite database
6. **Deliver**: Send formatted messages to Telegram with inline buttons
7. **Interact**: Handle user commands and callback queries

### Database Schema

**articles** table:
- `id`: Primary key
- `source`: Source name (hn, geeknews, github, producthunt)
- `url`: Article URL (unique)
- `title`: Article title
- `content`: Article content/description
- `created_at`: Timestamp

**summaries** table:
- `id`: Primary key
- `article_id`: Foreign key to articles
- `summary_text`: AI-generated summary
- `batch`: Batch type (morning, evening)
- `created_at`: Timestamp

**bookmarks** table:
- `id`: Primary key
- `user_id`: Telegram user ID
- `article_id`: Foreign key to articles
- `created_at`: Timestamp
- Unique constraint on (user_id, article_id)

**settings** table:
- `key`: Setting name
- `value`: Setting value
- Primary key on key

## Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_handlers.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Adding a New Data Source

1. Create a new fetcher in `src/fetchers/`:
   ```python
   from src.fetchers.base_fetcher import BaseFetcher
   
   class NewSourceFetcher(BaseFetcher):
       source_name = "newsource"
       
       async def fetch(self, limit: int = 10) -> list[dict]:
           # Implementation
           pass
   ```

2. Add to `src/fetchers/__init__.py`

3. Update `src/scheduler.py` to include the new fetcher

### Modifying Schedule Times

Via Telegram:
```
/settings
# Then follow prompts to change times
```

Via database:
```bash
sqlite3 digest.db "UPDATE settings SET value = '09:00' WHERE key = 'morning_time'"
sqlite3 digest.db "UPDATE settings SET value = '21:00' WHERE key = 'evening_time'"
sudo systemctl restart digest-bot
```

## License

[Specify your license here]

## Support

For issues and questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review logs: `journalctl -u digest-bot -n 100`
- Open an issue on GitHub (if applicable)
