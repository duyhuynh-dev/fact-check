"""Application configuration helpers."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development")
    database_dsn: str = Field(
        default="postgresql+psycopg://user:password@localhost:5432/factcheck"
    )
    ingest_bucket_path: str = Field(default="./data/uploads")
    processed_text_path: str = Field(default="./data/processed")
    vectorstore_path: str = Field(default="./vectorstore")
    docs_base_url: HttpUrl | None = Field(default=None)
    queue_backend: str = Field(default="sync")
    redis_dsn: str | None = Field(default=None)
    claim_extractor: str = Field(
        default="simple", description="simple | spacy | llm"
    )
    verification_provider: str = Field(
        default="gemini", description="gemini (free) | openai | free (mock)"
    )
    openai_api_key: str | None = Field(default=None)
    openai_model: str = Field(default="gpt-4o-mini")
    gemini_api_key: str | None = Field(default=None)
    gemini_model: str = Field(default="gemini-1.5-flash")
    free_mode: bool = Field(
        default=False,
        description="Free mode: uses local models and mock verification (no API costs)",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()

