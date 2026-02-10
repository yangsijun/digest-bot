"""Main entry point for digest-bot."""

import asyncio
import logging
from src.config import setup_logging, validate_config, DATABASE_PATH
from src.db import init_db
from src.bot.bot import create_application
from src.scheduler import start_scheduler

logger = logging.getLogger("digest_bot")


async def run_bot():
    """Run the Telegram bot and scheduler."""
    application = create_application()

    async with application:
        await application.initialize()
        await application.start()

        start_scheduler()
        logger.info("Scheduler started")

        await application.updater.start_polling()
        logger.info("Bot started polling")

        await asyncio.Event().wait()


def main():
    """Main function to start the digest bot."""
    setup_logging()
    logger.info("Starting digest-bot...")

    try:
        validate_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise

    try:
        init_db(DATABASE_PATH)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    logger.info("Digest-bot initialized successfully")

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Shutting down digest-bot...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
