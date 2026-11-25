import logging
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings

logger = logging.getLogger("defectiq.db")

if os.name == "nt":
    pg_root = Path("C:/Program Files/PostgreSQL")
    if pg_root.is_dir():
        for pg_bin in sorted(pg_root.glob("*/bin"), reverse=True):
            bin_str = str(pg_bin)
            if bin_str not in os.environ.get("PATH", ""):
                os.environ["PATH"] = f"{bin_str}{os.pathsep}{os.environ.get('PATH', '')}"

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=3600 if "postgres" in settings.database_url else -1
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> tuple[bool, str]:
    """Test database connectivity with a lightweight ping."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Database connection operational."
    except Exception as exc:
        logger.error(f"Database connection check failed: {exc}")
        return False, str(exc)


def init_db() -> None:
    """Create database tables and apply lightweight additive column checks."""
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for column in ("indexed_vectors", "skipped_records", "resume_offset"):
            try:
                conn.execute(text(f"ALTER TABLE ingestion_jobs ADD COLUMN {column} INTEGER NOT NULL DEFAULT 0"))
            except Exception:
                pass  # Existing database already has this column.
