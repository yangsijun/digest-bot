"""Search functionality for digest-bot."""

import logging
from typing import List, Dict
from .db import get_db_connection

logger = logging.getLogger("digest_bot")


def search_summaries(keyword: str, db_path: str = "digest.db") -> List[Dict]:
    """
    Search for summaries containing the keyword.

    Searches in article title and summary text (case-insensitive).

    Args:
        keyword: Search keyword
        db_path: Path to database file

    Returns:
        List of dicts containing article info, summary, and URL
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        # Use LIKE for case-insensitive search in title and summary_text
        query = """
            SELECT 
                a.id as article_id,
                a.source,
                a.url,
                a.title,
                s.summary_text,
                s.batch,
                s.created_at
            FROM summaries s
            JOIN articles a ON s.article_id = a.id
            WHERE 
                LOWER(a.title) LIKE LOWER(?) 
                OR LOWER(s.summary_text) LIKE LOWER(?)
            ORDER BY s.created_at DESC
        """

        search_pattern = f"%{keyword}%"
        cursor.execute(query, (search_pattern, search_pattern))

        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "article_id": row["article_id"],
                    "source": row["source"],
                    "url": row["url"],
                    "title": row["title"],
                    "summary_text": row["summary_text"],
                    "batch": row["batch"],
                    "created_at": row["created_at"],
                }
            )

        logger.info(f"Search for '{keyword}' returned {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"Search error: {e}")
        return []
    finally:
        conn.close()
