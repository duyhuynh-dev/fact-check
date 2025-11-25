"""SQLModel session and engine helpers."""

import os
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        dsn = os.environ.get("POSTGRES_DSN") or os.environ.get("DATABASE_DSN")
        if not dsn:
            from backend.app.core.config import get_settings

            dsn = get_settings().database_dsn
        _engine = create_engine(dsn, pool_pre_ping=True, echo=False)
    return _engine


def init_db() -> None:
    """Create database tables if they do not exist and run migrations."""
    SQLModel.metadata.create_all(bind=get_engine())
    # Run migrations for schema updates
    try:
        from backend.app.db.migrations import run_migrations
        run_migrations()
    except Exception as e:
        # Migration failures are non-fatal in development
        print(f"⚠️  Migration warning: {e}")


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped session."""
    with Session(get_engine()) as session:
        yield session

