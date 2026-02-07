"""
SQLite database configuration using SQLAlchemy.

Includes sqlite-vector extension for semantic search capabilities.
"""

import importlib.resources
import logging
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.settings import DATA_DIR as _DATA_DIR_STR

logger = logging.getLogger(__name__)

# Database file path - use /app/data in container, local data/ dir otherwise
DATA_DIR = Path(_DATA_DIR_STR)
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DATA_DIR / "waywo.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine with SQLite-specific settings
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite with threads
    echo=False,  # Set to True for SQL debugging
)


# Enable foreign key support and load vector extension in SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")

    # Load sqlite-vector extension
    try:
        ext_path = importlib.resources.files("sqlite_vector.binaries") / "vector"
        dbapi_connection.enable_load_extension(True)
        dbapi_connection.load_extension(str(ext_path))
        dbapi_connection.enable_load_extension(False)
        logger.debug("🔌 sqlite-vector extension loaded")

        # Initialize vector search for this connection
        # vector_init() must be called on each connection to set up the context
        cursor.execute(
            "SELECT vector_init('waywo_projects', 'description_embedding', "
            "'type=FLOAT32,dimension=4096,distance=COSINE')"
        )
        logger.debug("🔍 Vector search context initialized for connection")
    except Exception as e:
        logger.warning(f"⚠️ Could not load sqlite-vector extension: {e}")

    cursor.close()


# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


def get_db():
    """
    Dependency that provides a database session.
    Usage: db = next(get_db()) or with get_db() as db:
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize the database by creating all tables.
    Call this on application startup.
    """
    from src.db.models import WaywoCommentDB, WaywoPostDB, WaywoProjectDB

    Base.metadata.create_all(bind=engine)
    print(f"📦 Database initialized at {DATABASE_PATH}")

    # Safe migrations for new columns on existing databases
    _run_migrations()

    # Initialize vector search for projects table
    init_vector_search()


def _run_migrations():
    """Run safe ALTER TABLE migrations for new columns."""
    migrations = [
        "ALTER TABLE waywo_projects ADD COLUMN primary_url TEXT",
        "ALTER TABLE waywo_projects ADD COLUMN url_contents TEXT",
    ]
    with SessionLocal() as session:
        for sql in migrations:
            try:
                session.execute(text(sql))
                session.commit()
                logger.info(f"✅ Migration: {sql}")
            except Exception:
                session.rollback()
                # Column already exists, safe to ignore


def init_vector_search():
    """
    Initialize the sqlite-vector extension for the waywo_projects table.
    This sets up the vector metadata for similarity search.
    """
    try:
        with SessionLocal() as session:
            # Check if vector extension is available
            result = session.execute(text("SELECT vector_version()"))
            version = result.scalar()
            logger.info(f"🔍 sqlite-vector version: {version}")

            # Initialize vector index for description_embedding column
            # FLOAT32, 4096 dimensions (llama-embed-nemotron-8b), COSINE distance
            session.execute(
                text(
                    "SELECT vector_init('waywo_projects', 'description_embedding', "
                    "'type=FLOAT32,dimension=4096,distance=COSINE')"
                )
            )
            session.commit()
            logger.info(
                "✅ Vector search initialized for waywo_projects.description_embedding"
            )
    except Exception as e:
        logger.warning(f"⚠️ Could not initialize vector search: {e}")


def build_vector_index():
    """
    Build/rebuild the vector quantization index for fast similarity search.

    This must be called after adding/updating embeddings to enable
    vector_quantize_scan() searches. Safe to call multiple times.
    """
    try:
        with SessionLocal() as session:
            # Check if there are any embeddings to index
            result = session.execute(
                text(
                    "SELECT COUNT(*) FROM waywo_projects WHERE description_embedding IS NOT NULL"
                )
            )
            count = result.scalar()

            if count == 0:
                logger.info("📭 No embeddings to index yet, skipping vector_quantize()")
                return

            # Build the quantization index
            # This enables fast approximate nearest neighbor search
            logger.info(
                f"🔨 Building vector quantization index for {count} embeddings..."
            )
            session.execute(
                text(
                    "SELECT vector_quantize('waywo_projects', 'description_embedding')"
                )
            )
            session.commit()
            logger.info(f"✅ Vector quantization index built for {count} embeddings")
    except Exception as e:
        logger.warning(f"⚠️ Could not build vector quantization index: {e}")
