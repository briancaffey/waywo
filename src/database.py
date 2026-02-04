"""
SQLite database configuration using SQLAlchemy.

Includes sqlite-vector extension for semantic search capabilities.
"""

import importlib.resources
import logging
import os
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)

# Database file path - use /app/data in container, local data/ dir otherwise
DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
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
    from src.db_models import WaywoCommentDB, WaywoPostDB, WaywoProjectDB

    Base.metadata.create_all(bind=engine)
    print(f"📦 Database initialized at {DATABASE_PATH}")

    # Initialize vector search for projects table
    init_vector_search()


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
            logger.info("✅ Vector search initialized for waywo_projects.description_embedding")
    except Exception as e:
        logger.warning(f"⚠️ Could not initialize vector search: {e}")
