"""URL-based article deduplication logic."""

import logging
from datetime import date
from typing import Any
from urllib.parse import urlparse, urlunparse

from src.db import get_db_connection
from src.config import DATABASE_PATH

logger = logging.getLogger("digest_bot")

ARTICLES_PER_BATCH = 10


def normalize_url(url: str) -> str:
    """Normalize URL for case-insensitive comparison.

    - Lowercase scheme and netloc
    - Remove trailing slashes from path
    - Remove fragment
    """
    parsed = urlparse(url.strip())
    normalized = urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or "/",
            parsed.params,
            parsed.query,
            "",
        )
    )
    return normalized


def get_todays_sent_urls(batch: str, db_path: str = DATABASE_PATH) -> set[str]:
    """Get URLs of articles already sent today for the given batch.

    Args:
        batch: 'morning' or 'evening'
        db_path: Path to database

    Returns:
        Set of normalized URLs already sent today
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        today = date.today().isoformat()
        cursor.execute(
            """
            SELECT a.url FROM articles a
            JOIN summaries s ON a.id = s.article_id
            WHERE date(s.created_at) = ? AND s.batch = ?
            """,
            (today, batch),
        )
        rows = cursor.fetchall()
        return {normalize_url(row[0]) for row in rows}
    finally:
        conn.close()


def get_todays_all_sent_urls(db_path: str = DATABASE_PATH) -> set[str]:
    """Get all URLs sent today (both batches) to avoid overlap.

    Returns:
        Set of normalized URLs already sent today
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        today = date.today().isoformat()
        cursor.execute(
            """
            SELECT a.url FROM articles a
            JOIN summaries s ON a.id = s.article_id
            WHERE date(s.created_at) = ?
            """,
            (today,),
        )
        rows = cursor.fetchall()
        return {normalize_url(row[0]) for row in rows}
    finally:
        conn.close()


def deduplicate_articles(
    articles: list[dict[str, Any]],
    exclude_urls: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Deduplicate articles by URL.

    - Case-insensitive URL comparison
    - When duplicate found: keep first occurrence, add related_urls field
    - Excludes URLs in exclude_urls set (already sent articles)

    Args:
        articles: List of article dicts with 'url', 'title', 'content', 'source'
        exclude_urls: Set of normalized URLs to exclude (e.g., already sent today)

    Returns:
        Deduplicated list of articles (first occurrence kept, with related_urls)
    """
    if exclude_urls is None:
        exclude_urls = set()

    url_to_index: dict[str, int] = {}
    result: list[dict[str, Any]] = []

    for article in articles:
        url = article.get("url", "")
        if not url:
            continue

        normalized = normalize_url(url)

        if normalized in exclude_urls:
            logger.debug(f"Skipping already-sent URL: {url}")
            continue

        if normalized in url_to_index:
            idx = url_to_index[normalized]
            if "related_urls" not in result[idx]:
                result[idx]["related_urls"] = []
            result[idx]["related_urls"].append(
                {
                    "url": url,
                    "source": article.get("source", "unknown"),
                }
            )
            logger.debug(f"Duplicate found: {url} (source: {article.get('source')})")
        else:
            url_to_index[normalized] = len(result)
            result.append(article.copy())

    logger.info(f"Deduplicated {len(articles)} articles to {len(result)} unique items")
    return result


def select_balanced_articles(
    articles: list[dict[str, Any]],
    limit: int = ARTICLES_PER_BATCH,
) -> list[dict[str, Any]]:
    """Select articles balanced across sources.

    Attempts to pick evenly from all sources when possible.

    Args:
        articles: Deduplicated list of articles
        limit: Maximum number of articles to return

    Returns:
        Balanced selection of articles (up to limit)
    """
    if len(articles) <= limit:
        return articles

    by_source: dict[str, list[dict[str, Any]]] = {}
    for article in articles:
        source = article.get("source", "unknown")
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(article)

    result: list[dict[str, Any]] = []
    sources = list(by_source.keys())
    source_indices = {s: 0 for s in sources}

    while len(result) < limit:
        added_any = False
        for source in sources:
            if len(result) >= limit:
                break
            source_articles = by_source[source]
            idx = source_indices[source]
            if idx < len(source_articles):
                result.append(source_articles[idx])
                source_indices[source] = idx + 1
                added_any = True

        if not added_any:
            break

    logger.info(f"Selected {len(result)} articles balanced from {len(sources)} sources")
    return result


def prepare_batch_articles(
    articles: list[dict[str, Any]],
    batch: str,
    db_path: str = DATABASE_PATH,
) -> list[dict[str, Any]]:
    """Prepare articles for a digest batch.

    1. Exclude today's already-sent URLs (both batches)
    2. Deduplicate by URL
    3. Select balanced articles (up to 10)

    Args:
        articles: Raw articles from all fetchers
        batch: 'morning' or 'evening'
        db_path: Path to database

    Returns:
        List of up to 10 deduplicated, balanced articles
    """
    _ = batch
    exclude_urls = get_todays_all_sent_urls(db_path)
    logger.info(f"Excluding {len(exclude_urls)} URLs already sent today")

    unique_articles = deduplicate_articles(articles, exclude_urls)
    selected = select_balanced_articles(unique_articles, ARTICLES_PER_BATCH)

    return selected
