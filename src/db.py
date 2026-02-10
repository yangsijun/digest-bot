"""Database initialization and management for digest-bot."""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("digest_bot")


def get_db_connection(db_path: str = "digest.db"):
    """Get a database connection with WAL mode enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL;")

    return conn


def init_db(db_path: str = "digest.db"):
    """Initialize the database with required schema."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        # Create articles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create summaries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                summary_text TEXT NOT NULL,
                batch TEXT CHECK(batch IN ('morning', 'evening', 'manual')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
            )
        """)

        # Create bookmarks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                article_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
                UNIQUE(user_id, article_id)
            )
        """)

        # Create settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Create indexes for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_source 
            ON articles(source)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_created_at 
            ON articles(created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_summaries_article_id 
            ON summaries(article_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_summaries_batch 
            ON summaries(batch)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bookmarks_user_id 
            ON bookmarks(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bookmarks_article_id 
            ON bookmarks(article_id)
        """)

        conn.commit()
        logger.info(f"Database initialized successfully at {db_path}")

    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def get_setting(key: str, db_path: str = "digest.db") -> str | None:
    """Get a setting value from the database."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def set_setting(key: str, value: str, db_path: str = "digest.db"):
    """Set a setting value in the database."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )
        conn.commit()
    finally:
        conn.close()
