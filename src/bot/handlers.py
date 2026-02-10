import asyncio
import logging
from typing import List, Dict
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from ..db import get_db_connection
from ..summarizer import summarize_article
from .keyboards import get_article_keyboard

logger = logging.getLogger(__name__)


async def handle_detail_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    article_id = int(query.data.split(":")[1])
    logger.info(f"Detail requested for article {article_id}")

    await query.edit_message_text(
        text=f"📖 상세 분석을 요청했습니다 (Article ID: {article_id})\n\n[Placeholder: 상세 분석 결과가 여기에 표시됩니다]"
    )


async def handle_translate_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    article_id = int(query.data.split(":")[1])
    logger.info(f"Translation requested for article {article_id}")

    await query.edit_message_text(
        text=f"🇰🇷 한국어 번역을 요청했습니다 (Article ID: {article_id})\n\n[Placeholder: 번역 결과가 여기에 표시됩니다]"
    )


async def handle_bookmark_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query

    article_id = int(query.data.split(":")[1])
    user_id = str(query.from_user.id)

    success = save_bookmark(user_id, article_id)

    if success:
        await query.answer("북마크에 저장되었습니다!")
        await query.edit_message_text(
            text=f"🔖 북마크에 저장했습니다 (Article ID: {article_id})"
        )
        logger.info(f"Bookmark saved for user {user_id}, article {article_id}")
    else:
        await query.answer("이미 북마크에 저장된 글입니다.")
        await query.edit_message_text(
            text=f"🔖 이미 북마크에 저장된 글입니다 (Article ID: {article_id})"
        )


async def handle_related_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    article_id = int(query.data.split(":")[1])
    logger.info(f"Related articles requested for article {article_id}")

    await query.edit_message_text(
        text=f"🔗 관련 글을 검색했습니다 (Article ID: {article_id})\n\n[Placeholder: 관련 글 목록이 여기에 표시됩니다]"
    )


def save_bookmark(user_id: str, article_id: int, db_path: str = "digest.db") -> bool:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO bookmarks (user_id, article_id) VALUES (?, ?)",
            (user_id, article_id),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving bookmark: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


async def handle_digest_item_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    article_id = int(query.data.split(":")[1])

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, source, url, title, content FROM articles WHERE id = ?",
            (article_id,),
        )
        row = cursor.fetchone()
        if not row:
            await query.message.reply_text("기사를 찾을 수 없습니다.")
            return

        article = {
            "source": row["source"],
            "url": row["url"],
            "title": row["title"],
            "content": row["content"] or "",
        }

        cursor.execute(
            "SELECT summary_text FROM summaries WHERE article_id = ? ORDER BY id DESC LIMIT 1",
            (article_id,),
        )
        summary_row = cursor.fetchone()
    finally:
        conn.close()

    if summary_row and summary_row["summary_text"]:
        summary = summary_row["summary_text"]
    else:
        await query.message.reply_text(
            f"⏳ <b>{article['title']}</b> 요약 생성 중...",
            parse_mode=ParseMode.HTML,
        )
        summary = await asyncio.to_thread(summarize_article, article)
        if not summary:
            summary = "요약을 생성할 수 없습니다."

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO summaries (article_id, summary_text, batch) VALUES (?, ?, 'manual')",
                (article_id, summary),
            )
            conn.commit()
        finally:
            conn.close()

    source_emoji = {"hn": "🔶", "geeknews": "🇰🇷", "github": "🐙", "producthunt": "🚀"}
    emoji = source_emoji.get(article["source"], "📰")

    message_text = (
        f"<b>{emoji} {article['title']}</b>\n\n"
        f"{summary}\n\n"
        f'🔗 <a href="{article["url"]}">원문 보기</a>'
    )
    keyboard = get_article_keyboard(article_id)

    await query.message.reply_text(
        text=message_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


def get_bookmarks(user_id: str, db_path: str = "digest.db") -> List[Dict]:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        query = """
            SELECT 
                b.id as bookmark_id,
                b.created_at as bookmarked_at,
                a.id as article_id,
                a.source,
                a.url,
                a.title,
                s.summary_text
            FROM bookmarks b
            JOIN articles a ON b.article_id = a.id
            LEFT JOIN summaries s ON a.id = s.article_id
            WHERE b.user_id = ?
            ORDER BY b.created_at DESC
        """

        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "bookmark_id": row["bookmark_id"],
                    "bookmarked_at": row["bookmarked_at"],
                    "article_id": row["article_id"],
                    "source": row["source"],
                    "url": row["url"],
                    "title": row["title"],
                    "summary_text": row["summary_text"],
                }
            )

        return results

    except Exception as e:
        logger.error(f"Error getting bookmarks: {e}")
        return []
    finally:
        conn.close()
