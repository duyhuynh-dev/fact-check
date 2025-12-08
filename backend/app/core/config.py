"""Application configuration helpers."""

from functools import lru_cache
from pathlib import Path
from typing import List, Union
import json

from pydantic import Field, HttpUrl, field_validator
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
        default="sqlite:///./factcheck.db"
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
    evidence_min_similarity: float = Field(
        default=0.3,
        description="Minimum similarity threshold for evidence retrieval (0.0-1.0)",
    )
    evidence_retrieval_limit: int = Field(
        default=5,
        description="Maximum number of evidence snippets to retrieve per claim",
    )
    cors_origins: List[str] = Field(
        default=["https://*.vercel.app", "http://localhost:3000", "http://127.0.0.1:3000"],
        description="List of allowed CORS origins. Supports wildcards like 'https://*.vercel.app'.",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from JSON string or comma-separated string."""
        if isinstance(v, str):
            # Try parsing as JSON first
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
            # Fall back to comma-separated
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()

