"""Main entry point for digest-bot."""

import logging
from src.config import setup_logging, validate_config, DATABASE_PATH
from src.db import init_db

logger = logging.getLogger("digest_bot")


def main():
    """Main function to start the digest bot."""
    # Setup logging
    setup_logging()

    logger.info("Starting digest-bot...")

    # Validate configuration
    try:
        validate_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise

    # Initialize database
    try:
        init_db(DATABASE_PATH)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    logger.info("Digest-bot initialized successfully")

    # TODO: Add bot startup logic here


if __name__ == "__main__":
    main()
