# Digest Bot

A Telegram bot for aggregating and summarizing news from multiple sources.

## Project Structure

```
digest-bot/
├── src/
│   ├── __init__.py
│   ├── main.py           # Entry point
│   ├── config.py         # Configuration management
│   ├── db.py             # Database initialization and management
│   ├── fetchers/         # News source fetchers
│   ├── bot/              # Telegram bot logic
│   └── auth/             # Authentication module
├── tests/                # Test suite
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

4. Initialize the database:
   ```bash
   python -c "from src.db import init_db; init_db()"
   ```

## Running the Bot

```bash
python -m src.main
```

## Database Schema

The bot uses SQLite with the following tables:

- **articles**: Stores news articles from various sources
- **summaries**: Stores AI-generated summaries of articles
- **bookmarks**: Stores user bookmarks
- **settings**: Stores application settings

All database operations use raw SQL (no ORM) for simplicity and performance.
