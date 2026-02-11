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
    from src.db.database import (
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
                text("ALTER TABLE waywo_projects ADD COLUMN screenshot_path TEXT")
            )
            conn.commit()
            logger.info("Added screenshot_path column to waywo_projects")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                logger.info("screenshot_path column already exists")
            else:
                logger.warning(f"Could not add screenshot_path column: {e}")

        # Add UMAP cluster map columns
        for col_name, col_def in [
            ("umap_x", "REAL"),
            ("umap_y", "REAL"),
            ("cluster_label", "INTEGER"),
        ]:
            try:
                conn.execute(
                    text(f"ALTER TABLE waywo_projects ADD COLUMN {col_name} {col_def}")
                )
                conn.commit()
                logger.info(f"Added {col_name} column to waywo_projects")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    logger.info(f"{col_name} column already exists")
                else:
                    logger.warning(f"Could not add {col_name} column: {e}")

        # Add source column to waywo_projects if it doesn't exist
        try:
            conn.execute(
                text("ALTER TABLE waywo_projects ADD COLUMN source VARCHAR(50)")
            )
            conn.commit()
            logger.info("Added source column to waywo_projects")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                logger.info("source column already exists")
            else:
                logger.warning(f"Could not add source column: {e}")

        # Make source_comment_id nullable (SQLite requires table rebuild)
        try:
            # Check if source_comment_id is still NOT NULL
            cols = conn.execute(
                text("PRAGMA table_info(waywo_projects)")
            ).fetchall()
            src_col = [c for c in cols if c[1] == "source_comment_id"]
            if src_col and src_col[0][3] == 1:  # notnull == 1
                logger.info(
                    "Rebuilding waywo_projects to make source_comment_id nullable..."
                )
                # Get all current column names/types from PRAGMA
                col_names = [c[1] for c in cols]
                col_list = ", ".join(col_names)

                # Build CREATE TABLE with nullable source_comment_id
                # We read the original DDL and modify it
                original_ddl = conn.execute(
                    text(
                        "SELECT sql FROM sqlite_master WHERE type='table' AND name='waywo_projects'"
                    )
                ).scalar()

                # Replace NOT NULL on source_comment_id with nullable
                new_ddl = original_ddl.replace(
                    "waywo_projects", "waywo_projects_tmp", 1
                )
                # Remove NOT NULL constraint from source_comment_id line
                # The column def looks like: source_comment_id INTEGER NOT NULL
                new_ddl = new_ddl.replace(
                    "source_comment_id INTEGER NOT NULL",
                    "source_comment_id INTEGER",
                )

                conn.execute(text(new_ddl))
                conn.execute(
                    text(
                        f"INSERT INTO waywo_projects_tmp ({col_list}) SELECT {col_list} FROM waywo_projects"
                    )
                )
                conn.execute(text("DROP TABLE waywo_projects"))
                conn.execute(
                    text(
                        "ALTER TABLE waywo_projects_tmp RENAME TO waywo_projects"
                    )
                )
                conn.commit()
                logger.info("source_comment_id is now nullable")

                # Recreate indexes that were dropped with the table
                for idx_sql in [
                    "CREATE INDEX IF NOT EXISTS ix_waywo_projects_source_comment_id ON waywo_projects (source_comment_id)",
                    "CREATE INDEX IF NOT EXISTS ix_waywo_projects_idea_score ON waywo_projects (idea_score)",
                    "CREATE INDEX IF NOT EXISTS ix_waywo_projects_complexity_score ON waywo_projects (complexity_score)",
                    "CREATE INDEX IF NOT EXISTS ix_waywo_projects_is_valid ON waywo_projects (is_valid_project)",
                    "CREATE INDEX IF NOT EXISTS ix_waywo_projects_created_at ON waywo_projects (created_at)",
                    "CREATE INDEX IF NOT EXISTS ix_waywo_projects_source ON waywo_projects (source)",
                ]:
                    conn.execute(text(idx_sql))
                conn.commit()
                logger.info("Recreated indexes on waywo_projects")
            else:
                logger.info("source_comment_id is already nullable")
        except Exception as e:
            logger.warning(f"Could not make source_comment_id nullable: {e}")

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
