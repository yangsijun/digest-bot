from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

SOURCE_EMOJI: dict[str, str] = {
    "hn": "🔶",
    "geeknews": "🇰🇷",
    "github": "🐙",
    "producthunt": "🚀",
}


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


def get_digest_list_keyboard(
    saved: list[tuple[int, dict[str, Any]]],
) -> InlineKeyboardMarkup:
    buttons: list[InlineKeyboardButton] = []
    for idx, (article_id, article) in enumerate(saved, 1):
        source = article.get("source", "unknown")
        emoji = SOURCE_EMOJI.get(source, "📰")
        buttons.append(
            InlineKeyboardButton(
                f"{idx}. {emoji}",
                callback_data=f"digest_item:{article_id}",
            )
        )

    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(buttons), 5):
        rows.append(buttons[i : i + 5])

    return InlineKeyboardMarkup(rows)
