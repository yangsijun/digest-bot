"""Settings management for digest-bot."""

import logging
from typing import Dict
from .db import get_db_connection

logger = logging.getLogger("digest_bot")


def get_schedule_times(db_path: str = "digest.db") -> Dict[str, str]:
    """
    Get morning and evening schedule times from database.

    Args:
        db_path: Path to database file

    Returns:
        Dict with 'morning_time' and 'evening_time' keys
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT key, value FROM settings WHERE key IN ('morning_time', 'evening_time')"
        )
        rows = cursor.fetchall()

        result = {"morning_time": "09:00", "evening_time": "21:00"}

        for row in rows:
            result[row["key"]] = row["value"]

        return result

    except Exception as e:
        logger.error(f"Error getting schedule times: {e}")
        return {"morning_time": "09:00", "evening_time": "21:00"}
    finally:
        conn.close()


def update_schedule(morning: str, evening: str, db_path: str = "digest.db") -> bool:
    """
    Update morning and evening schedule times in database.

    Args:
        morning: Morning time in HH:MM format
        evening: Evening time in HH:MM format
        db_path: Path to database file

    Returns:
        True if successful, False otherwise
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('morning_time', ?)",
            (morning,),
        )
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('evening_time', ?)",
            (evening,),
        )
        conn.commit()
        logger.info(f"Schedule updated: morning={morning}, evening={evening}")
        return True

    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
