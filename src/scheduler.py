"""APScheduler configuration for digest generation."""

import asyncio
import fcntl
import logging
from pathlib import Path
from typing import Any, TextIO

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from telegram.constants import ParseMode

from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DATABASE_PATH
from src.db import get_db_connection, init_db
from src.fetchers import HNFetcher, GeekNewsFetcher, GitHubFetcher, ProductHuntFetcher
from src.summarizer import summarize_article
from src.dedup import prepare_batch_articles
from src.bot.keyboards import get_article_keyboard

logger = logging.getLogger("digest_bot")

LOCK_FILE_PATH = Path("/tmp/digest_bot.lock")
TIMEZONE = "Asia/Seoul"


class DigestLock:
    lock_path: Path
    _lock_file: TextIO | None

    def __init__(self, lock_path: Path = LOCK_FILE_PATH):
        self.lock_path = lock_path
        self._lock_file = None

    def __enter__(self) -> "DigestLock":
        self._lock_file = open(self.lock_path, "w")
        try:
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return self
        except BlockingIOError:
            self._lock_file.close()
            raise RuntimeError("Another digest job is already running")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        if self._lock_file:
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
            self._lock_file.close()


async def fetch_all_sources(limit_per_source: int = 10) -> list[dict[str, Any]]:
    fetchers = [
        HNFetcher(),
        GeekNewsFetcher(),
        GitHubFetcher(),
        ProductHuntFetcher(),
    ]

    all_articles: list[dict[str, Any]] = []
    tasks = [fetcher.fetch(limit=limit_per_source) for fetcher in fetchers]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for fetcher, result in zip(fetchers, results):
        if isinstance(result, BaseException):
            logger.error(f"Failed to fetch from {fetcher.source_name}: {result}")
            continue
        all_articles.extend(result)
        logger.info(f"Fetched {len(result)} articles from {fetcher.source_name}")

    return all_articles


def save_article_to_db(article: dict[str, Any], db_path: str = DATABASE_PATH) -> int:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT OR IGNORE INTO articles (source, url, title, content)
            VALUES (?, ?, ?, ?)
            """,
            (
                article.get("source", "unknown"),
                article["url"],
                article["title"],
                article.get("content", ""),
            ),
        )
        conn.commit()

        cursor.execute("SELECT id FROM articles WHERE url = ?", (article["url"],))
        row = cursor.fetchone()
        return row[0] if row else -1
    finally:
        conn.close()


def save_summary_to_db(
    article_id: int,
    summary_text: str,
    batch: str,
    db_path: str = DATABASE_PATH,
) -> int:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO summaries (article_id, summary_text, batch)
            VALUES (?, ?, ?)
            """,
            (article_id, summary_text, batch),
        )
        conn.commit()
        return cursor.lastrowid or -1
    finally:
        conn.close()


def format_digest_message(
    article: dict[str, Any],
    summary: str,
    index: int,
    total: int,
) -> str:
    source_emoji = {
        "hn": "🔶",
        "geeknews": "🇰🇷",
        "github": "🐙",
        "producthunt": "🚀",
    }
    source = article.get("source", "unknown")
    emoji = source_emoji.get(source, "📰")

    related_text = ""
    if "related_urls" in article:
        sources = [r.get("source", "?") for r in article["related_urls"]]
        related_text = f"\n🔗 Also on: {', '.join(sources)}"

    return (
        f"<b>{emoji} [{index}/{total}] {article['title']}</b>\n\n"
        f"{summary}\n"
        f"{related_text}\n"
        f'🔗 <a href="{article["url"]}">원문 보기</a>'
    )


async def send_digest_message(
    bot: Bot,
    chat_id: str,
    article: dict[str, Any],
    article_id: int,
    summary: str,
    index: int,
    total: int,
) -> None:
    message_text = format_digest_message(article, summary, index, total)
    keyboard = get_article_keyboard(article_id)

    await bot.send_message(
        chat_id=chat_id,
        text=message_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


async def run_digest(batch: str) -> None:
    logger.info(f"Starting {batch} digest generation")

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured")
        return

    try:
        with DigestLock():
            init_db(DATABASE_PATH)

            raw_articles = await fetch_all_sources()
            if not raw_articles:
                logger.warning("No articles fetched from any source")
                return

            articles = prepare_batch_articles(raw_articles, batch, DATABASE_PATH)
            if not articles:
                logger.warning("No articles after deduplication")
                return

            logger.info(f"Processing {len(articles)} articles for {batch} digest")

            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            total = len(articles)

            batch_header = "🌅 아침" if batch == "morning" else "🌙 저녁"
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=(
                    f"<b>{batch_header} 테크 다이제스트</b>\n\n"
                    f"📰 오늘의 뉴스 {total}개를 요약해서 보내드립니다."
                ),
                parse_mode=ParseMode.HTML,
            )

            for idx, article in enumerate(articles, 1):
                article_id = save_article_to_db(article, DATABASE_PATH)

                summary = summarize_article(article)
                if not summary:
                    summary = "요약을 생성할 수 없습니다."

                _ = save_summary_to_db(article_id, summary, batch, DATABASE_PATH)

                await send_digest_message(
                    bot,
                    TELEGRAM_CHAT_ID,
                    article,
                    article_id,
                    summary,
                    idx,
                    total,
                )

                await asyncio.sleep(1)

            logger.info(f"Completed {batch} digest: sent {total} articles")

    except RuntimeError as e:
        logger.warning(f"Digest job skipped: {e}")


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    scheduler.add_job(
        run_digest,
        CronTrigger(hour=8, minute=0, timezone=TIMEZONE),
        args=["morning"],
        id="morning_digest",
        replace_existing=True,
    )

    scheduler.add_job(
        run_digest,
        CronTrigger(hour=20, minute=0, timezone=TIMEZONE),
        args=["evening"],
        id="evening_digest",
        replace_existing=True,
    )

    logger.info("Scheduler configured: 08:00 and 20:00 KST")
    return scheduler


def start_scheduler() -> AsyncIOScheduler:
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started")
    return scheduler
