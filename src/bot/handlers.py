import logging
from telegram import Update
from telegram.ext import ContextTypes

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
    await query.answer("북마크에 저장되었습니다!")

    article_id = int(query.data.split(":")[1])
    logger.info(f"Bookmark saved for article {article_id}")

    await query.edit_message_text(
        text=f"🔖 북마크에 저장했습니다 (Article ID: {article_id})"
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
