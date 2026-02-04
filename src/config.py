"""Configuration management for digest-bot."""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Database configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "digest.db")

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Product Hunt API configuration
PRODUCTHUNT_CLIENT_ID = os.getenv("PRODUCTHUNT_CLIENT_ID")
PRODUCTHUNT_CLIENT_SECRET = os.getenv("PRODUCTHUNT_CLIENT_SECRET")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "digest_bot.log")


# Validate required configuration
def validate_config():
    """Validate that all required configuration is present."""
    required_vars = [
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )


def setup_logging():
    """Configure logging to both file and console."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    # Create logger
    logger = logging.getLogger("digest_bot")
    logger.setLevel(log_level)

    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
