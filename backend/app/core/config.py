"""Application configuration helpers."""

from functools import lru_cache
import os
from pydantic import BaseModel, Field, HttpUrl


class Settings(BaseModel):
    """Basic settings object populated from environment variables."""

    app_env: str = Field(default=os.getenv("APP_ENV", "development"))
    database_dsn: str = Field(
        default=os.getenv(
            "POSTGRES_DSN",
            "postgresql+psycopg://user:password@localhost:5432/factcheck",
        )
    )
    ingest_bucket_path: str = Field(
        default=os.getenv("INGEST_BUCKET_PATH", "./data/uploads")
    )
    processed_text_path: str = Field(
        default=os.getenv("PROCESSED_TEXT_PATH", "./data/processed")
    )
    vectorstore_path: str = Field(
        default=os.getenv("VECTORSTORE_PATH", "./vectorstore")
    )
    docs_base_url: HttpUrl | None = Field(
        default=os.getenv("DOCS_BASE_URL", "https://example.org/docs")
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()

