import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Chat, Message
from telegram.ext import ContextTypes

from src.bot.bot import start_command, help_command, is_authorized
from src.bot.utils import split_message


@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    return MagicMock(spec=ContextTypes.DEFAULT_TYPE)


class TestIsAuthorized:
    @patch("src.bot.bot.TELEGRAM_CHAT_ID", "12345")
    def test_authorized_user(self, mock_update):
        assert is_authorized(mock_update) is True

    @patch("src.bot.bot.TELEGRAM_CHAT_ID", "99999")
    def test_unauthorized_user(self, mock_update):
        assert is_authorized(mock_update) is False

    @patch("src.bot.bot.TELEGRAM_CHAT_ID", "12345")
    def test_no_effective_chat(self):
        update = MagicMock(spec=Update)
        update.effective_chat = None
        assert is_authorized(update) is False


class TestStartCommand:
    @pytest.mark.asyncio
    @patch("src.bot.bot.TELEGRAM_CHAT_ID", "12345")
    async def test_start_returns_welcome_message(self, mock_update, mock_context):
        await start_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        message = call_args[0][0]

        assert "<b>Tech Digest Bot</b>" in message
        assert "/start" in message
        assert "/help" in message
        assert "/digest" in message

    @pytest.mark.asyncio
    @patch("src.bot.bot.TELEGRAM_CHAT_ID", "99999")
    async def test_start_ignores_unauthorized_user(self, mock_update, mock_context):
        await start_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_not_called()


class TestHelpCommand:
    @pytest.mark.asyncio
    @patch("src.bot.bot.TELEGRAM_CHAT_ID", "12345")
    async def test_help_returns_help_text(self, mock_update, mock_context):
        await help_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        message = call_args[0][0]

        assert "<b>도움말</b>" in message


class TestSplitMessage:
    def test_empty_string_returns_empty_list(self):
        assert split_message("") == []

    def test_short_message_returns_single_chunk(self):
        text = "Hello, World!"
        result = split_message(text, max_len=100)
        assert result == [text]

    def test_splits_on_paragraph_boundary(self):
        text = "First paragraph.\n\nSecond paragraph."
        result = split_message(text, max_len=20)

        assert len(result) == 2
        assert result[0] == "First paragraph."
        assert result[1] == "Second paragraph."

    def test_preserves_paragraphs_when_possible(self):
        para1 = "A" * 100
        para2 = "B" * 100
        text = f"{para1}\n\n{para2}"

        result = split_message(text, max_len=150)

        assert len(result) == 2
        assert result[0] == para1
        assert result[1] == para2

    def test_splits_on_newline_when_no_paragraph_break(self):
        text = "Line one\nLine two\nLine three"
        result = split_message(text, max_len=15)

        assert all(len(chunk) <= 15 for chunk in result)
        assert "Line one" in result[0]

    def test_splits_on_space_when_no_newlines(self):
        text = "word1 word2 word3 word4"
        result = split_message(text, max_len=12)

        assert all(len(chunk) <= 12 for chunk in result)

    def test_hard_split_when_no_break_points(self):
        text = "A" * 5000
        result = split_message(text, max_len=4000)

        assert len(result) == 2
        assert all(len(chunk) <= 4000 for chunk in result)
        assert "".join(result) == text

    def test_all_chunks_within_max_len(self):
        text = "A" * 10000
        result = split_message(text, max_len=4000)

        assert all(len(chunk) <= 4000 for chunk in result)
