"""SQLModel session and engine helpers."""

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from backend.app.core.config import get_settings

_settings = get_settings()
engine = create_engine(_settings.database_dsn, pool_pre_ping=True, echo=False)


def init_db() -> None:
    """Create database tables if they do not exist."""
    SQLModel.metadata.create_all(bind=engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped session."""
    with Session(engine) as session:
        yield session

