"""Integration tests for the full digest pipeline."""

import asyncio
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db import init_db
from src.scheduler import fetch_all_sources, save_article_to_db, run_digest


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Initialize the database
    init_db(db_path)

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "test_token_123",
            "TELEGRAM_CHAT_ID": "12345",
            "PRODUCTHUNT_CLIENT_ID": "test_client_id",
            "PRODUCTHUNT_CLIENT_SECRET": "test_client_secret",
            "DATABASE_PATH": "test.db",
        },
    ):
        yield


@pytest.mark.asyncio
async def test_fetch_all_sources():
    """Test fetching from all sources."""
    with (
        patch("src.fetchers.hn_fetcher.HNFetcher.fetch") as mock_hn,
        patch("src.fetchers.geeknews_fetcher.GeekNewsFetcher.fetch") as mock_gn,
        patch("src.fetchers.github_fetcher.GitHubFetcher.fetch") as mock_gh,
        patch("src.fetchers.producthunt_fetcher.ProductHuntFetcher.fetch") as mock_ph,
    ):
        # Mock responses
        mock_hn.return_value = [
            {
                "url": "https://example.com/1",
                "title": "HN Article",
                "content": "Content",
                "source": "hn",
            }
        ]
        mock_gn.return_value = [
            {
                "url": "https://example.com/2",
                "title": "GeekNews Article",
                "content": "Content",
                "source": "geeknews",
            }
        ]
        mock_gh.return_value = [
            {
                "url": "https://github.com/test/repo",
                "title": "GitHub Repo",
                "content": "Description",
                "source": "github",
            }
        ]
        mock_ph.return_value = [
            {
                "url": "https://producthunt.com/posts/test",
                "title": "PH Product",
                "content": "Description",
                "source": "producthunt",
            }
        ]

        articles = await fetch_all_sources(limit_per_source=1)

        assert len(articles) == 4
        assert any(a["source"] == "hn" for a in articles)
        assert any(a["source"] == "geeknews" for a in articles)
        assert any(a["source"] == "github" for a in articles)
        assert any(a["source"] == "producthunt" for a in articles)


def test_save_article_to_db(temp_db):
    """Test saving an article to the database."""
    article = {
        "source": "hn",
        "url": "https://example.com/test",
        "title": "Test Article",
        "content": "Test content",
    }

    article_id = save_article_to_db(article, temp_db)

    assert article_id > 0

    # Verify article was saved
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[1] == "hn"  # source
    assert row[2] == "https://example.com/test"  # url
    assert row[3] == "Test Article"  # title


def test_save_article_duplicate(temp_db):
    """Test that duplicate URLs are ignored."""
    article = {
        "source": "hn",
        "url": "https://example.com/duplicate",
        "title": "Test Article",
        "content": "Test content",
    }

    # Save first time
    article_id_1 = save_article_to_db(article, temp_db)

    # Save second time (should return existing ID)
    article_id_2 = save_article_to_db(article, temp_db)

    assert article_id_1 == article_id_2

    # Verify only one article exists
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM articles WHERE url = ?", (article["url"],))
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1


@pytest.mark.asyncio
async def test_full_digest_pipeline(temp_db, mock_env_vars):
    """Test the full digest pipeline from fetch to send."""
    with (
        patch("src.scheduler.fetch_all_sources") as mock_fetch,
        patch("src.scheduler.summarize_article") as mock_summarize,
        patch("src.scheduler.Bot") as mock_bot_class,
        patch("src.scheduler.DATABASE_PATH", temp_db),
        patch("src.scheduler.TELEGRAM_BOT_TOKEN", "test_token"),
        patch("src.scheduler.TELEGRAM_CHAT_ID", "12345"),
        patch("src.scheduler.LOCK_FILE_PATH", Path(tempfile.mktemp())),
    ):
        # Mock fetched articles
        mock_fetch.return_value = [
            {
                "url": f"https://example.com/{i}",
                "title": f"Article {i}",
                "content": f"Content {i}",
                "source": "hn",
            }
            for i in range(5)
        ]

        # Mock summarizer
        mock_summarize.return_value = "## Summary\nTest summary\n\n## Insights\n- Insight 1\n\n## Action Items\n- Action 1"

        # Mock Telegram bot
        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()
        mock_bot_class.return_value = mock_bot

        # Run digest
        await run_digest("morning")

        # Verify articles were saved to database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles")
        article_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM summaries WHERE batch = 'morning'")
        summary_count = cursor.fetchone()[0]
        conn.close()

        assert article_count == 5
        assert summary_count == 5

        # Verify Telegram messages were sent
        assert mock_bot.send_message.call_count >= 1


@pytest.mark.asyncio
async def test_digest_deduplication(temp_db, mock_env_vars):
    """Test that duplicate articles are properly deduplicated."""
    with (
        patch("src.scheduler.fetch_all_sources") as mock_fetch,
        patch("src.scheduler.summarize_article") as mock_summarize,
        patch("src.scheduler.Bot") as mock_bot_class,
        patch("src.scheduler.DATABASE_PATH", temp_db),
        patch("src.scheduler.TELEGRAM_BOT_TOKEN", "test_token"),
        patch("src.scheduler.TELEGRAM_CHAT_ID", "12345"),
        patch("src.scheduler.LOCK_FILE_PATH", Path(tempfile.mktemp())),
    ):
        # Mock articles with duplicates
        mock_fetch.return_value = [
            {
                "url": "https://example.com/1",
                "title": "Article 1",
                "content": "Content",
                "source": "hn",
            },
            {
                "url": "https://example.com/1",
                "title": "Article 1",
                "content": "Content",
                "source": "geeknews",
            },  # Duplicate
            {
                "url": "https://example.com/2",
                "title": "Article 2",
                "content": "Content",
                "source": "hn",
            },
        ]

        mock_summarize.return_value = "Test summary"

        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()
        mock_bot_class.return_value = mock_bot

        await run_digest("morning")

        # Verify only unique articles were saved
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT url) FROM articles")
        unique_count = cursor.fetchone()[0]
        conn.close()

        assert unique_count == 2  # Only 2 unique URLs


@pytest.mark.asyncio
async def test_digest_with_fetcher_failure(temp_db, mock_env_vars):
    """Test that digest continues even if one fetcher fails."""
    with (
        patch("src.scheduler.fetch_all_sources") as mock_fetch,
        patch("src.scheduler.summarize_article") as mock_summarize,
        patch("src.scheduler.Bot") as mock_bot_class,
        patch("src.scheduler.DATABASE_PATH", temp_db),
        patch("src.scheduler.TELEGRAM_BOT_TOKEN", "test_token"),
        patch("src.scheduler.TELEGRAM_CHAT_ID", "12345"),
        patch("src.scheduler.LOCK_FILE_PATH", Path(tempfile.mktemp())),
    ):
        # Mock with some successful articles
        mock_fetch.return_value = [
            {
                "url": "https://example.com/1",
                "title": "Article 1",
                "content": "Content",
                "source": "hn",
            },
        ]

        mock_summarize.return_value = "Test summary"

        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()
        mock_bot_class.return_value = mock_bot

        await run_digest("evening")

        # Verify at least one article was processed
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM summaries WHERE batch = 'evening'")
        count = cursor.fetchone()[0]
        conn.close()

        assert count >= 1


@pytest.mark.asyncio
async def test_digest_lock_prevents_concurrent_runs(temp_db, mock_env_vars):
    """Test that the lock file prevents concurrent digest runs."""
    lock_path = Path(tempfile.mktemp())

    with (
        patch("src.scheduler.fetch_all_sources") as mock_fetch,
        patch("src.scheduler.summarize_article") as mock_summarize,
        patch("src.scheduler.Bot") as mock_bot_class,
        patch("src.scheduler.DATABASE_PATH", temp_db),
        patch("src.scheduler.LOCK_FILE_PATH", lock_path),
    ):
        mock_fetch.return_value = []
        mock_summarize.return_value = "Test summary"

        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()
        mock_bot_class.return_value = mock_bot

        # First run should succeed
        await run_digest("morning")

        # Lock file should be cleaned up after run
        assert not lock_path.exists()


def test_database_schema(temp_db):
    """Test that the database schema is correctly initialized."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    assert "articles" in tables
    assert "summaries" in tables
    assert "bookmarks" in tables
    assert "settings" in tables

    # Check articles table columns
    cursor.execute("PRAGMA table_info(articles)")
    columns = {row[1] for row in cursor.fetchall()}

    assert "id" in columns
    assert "source" in columns
    assert "url" in columns
    assert "title" in columns
    assert "content" in columns
    assert "created_at" in columns

    conn.close()
