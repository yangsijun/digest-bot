"""Main Telegram bot application."""

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram.constants import ParseMode

from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.bot.handlers import (
    handle_detail_callback,
    handle_translate_callback,
    handle_bookmark_callback,
    handle_related_callback,
)

logger = logging.getLogger(__name__)


def is_authorized(update: Update) -> bool:
    chat_id = str(update.effective_chat.id) if update.effective_chat else None
    return chat_id == TELEGRAM_CHAT_ID


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    effective_chat = update.effective_chat
    message = update.message

    if not is_authorized(update):
        chat_id = effective_chat.id if effective_chat else "unknown"
        logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
        return

    if not message:
        return

    welcome_message = (
        "<b>Tech Digest Bot</b>\n\n"
        "AI 기반 기술 뉴스 다이제스트 봇입니다.\n\n"
        "<b>명령어:</b>\n"
        "/start - 시작 메시지\n"
        "/help - 도움말\n"
        "/digest - 오늘의 다이제스트 생성"
    )
    await message.reply_text(welcome_message, parse_mode=ParseMode.HTML)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    message = update.message
    if not is_authorized(update) or not message:
        return

    help_text = (
        "<b>도움말</b>\n\n"
        "<b>사용 가능한 명령어:</b>\n"
        "/start - 봇 시작 및 환영 메시지\n"
        "/help - 이 도움말 표시\n"
        "/digest - 오늘의 기술 뉴스 다이제스트 생성\n\n"
        "<b>기능:</b>\n"
        "• Hacker News, GeekNews, Product Hunt, GitHub 트렌딩에서 뉴스 수집\n"
        "• AI 기반 요약 및 한국어 번역\n"
        "• 북마크 및 관련 글 검색"
    )
    await message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    message = update.message
    if not is_authorized(update) or not message:
        return

    await message.reply_text(
        "다이제스트를 생성 중입니다... 잠시만 기다려주세요.", parse_mode=ParseMode.HTML
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = update
    logger.error(
        f"Exception while handling update: {context.error}", exc_info=context.error
    )


def create_application() -> Application:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("digest", digest_command))

    application.add_handler(
        CallbackQueryHandler(handle_detail_callback, pattern=r"^detail:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_translate_callback, pattern=r"^translate:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_bookmark_callback, pattern=r"^bookmark:")
    )
    application.add_handler(
        CallbackQueryHandler(handle_related_callback, pattern=r"^related:")
    )

    application.add_error_handler(error_handler)

    return application


def run_bot() -> None:
    logger.info("Starting Telegram bot...")
    application = create_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)
