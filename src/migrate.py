#!/usr/bin/env python
"""
Database migration script.

Run this before starting the application to ensure the database schema
and vector search indexes are properly initialized.

Usage:
    python -m src.migrate
"""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_migrations():
    """Run all database migrations."""
    logger.info("Starting database migrations...")

    # Import here to ensure logging is configured first
    from src.database import (
        DATABASE_PATH,
        build_vector_index,
        init_db,
        init_vector_search,
        engine,
    )
    from sqlalchemy import text

    logger.info(f"Database path: {DATABASE_PATH}")

    # Initialize database tables
    logger.info("Creating database tables...")
    init_db()

    # Run column migrations for existing tables
    logger.info("Running column migrations...")
    with engine.connect() as conn:
        # Add is_bookmarked column to waywo_projects if it doesn't exist
        try:
            conn.execute(
                text(
                    "ALTER TABLE waywo_projects ADD COLUMN is_bookmarked BOOLEAN NOT NULL DEFAULT 0"
                )
            )
            conn.commit()
            logger.info("Added is_bookmarked column to waywo_projects")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                logger.info("is_bookmarked column already exists")
            else:
                logger.warning(f"Could not add is_bookmarked column: {e}")

        # Add screenshot_path column to waywo_projects if it doesn't exist
        try:
            conn.execute(
                text(
                    "ALTER TABLE waywo_projects ADD COLUMN screenshot_path TEXT"
                )
            )
            conn.commit()
            logger.info("Added screenshot_path column to waywo_projects")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                logger.info("screenshot_path column already exists")
            else:
                logger.warning(f"Could not add screenshot_path column: {e}")

    # Explicitly re-run vector search init to ensure it's set up
    # This is idempotent - safe to run multiple times
    logger.info("Initializing vector search indexes...")
    init_vector_search()

    # Build/rebuild the vector quantization index for fast searches
    logger.info("Building vector quantization index...")
    build_vector_index()

    logger.info("Database migrations completed successfully!")
    return True


def main():
    """Main entry point for migration script."""
    try:
        success = run_migrations()
        if success:
            logger.info("All migrations completed successfully")
            sys.exit(0)
        else:
            logger.error("Migrations failed")
            sys.exit(1)
    except Exception as e:
        logger.exception(f"Migration failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
