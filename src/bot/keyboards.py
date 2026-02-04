from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_article_keyboard(article_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📖 상세 보기", callback_data=f"detail:{article_id}"),
            InlineKeyboardButton(
                "🇰🇷 한국어 번역", callback_data=f"translate:{article_id}"
            ),
        ],
        [
            InlineKeyboardButton("🔖 북마크", callback_data=f"bookmark:{article_id}"),
            InlineKeyboardButton("🔗 관련 글", callback_data=f"related:{article_id}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
