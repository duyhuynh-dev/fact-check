"""Test package for fact-check API."""

import os

from backend.app.core.config import get_settings

os.environ.setdefault("POSTGRES_DSN", "sqlite:///./tests/test.db")
os.environ.setdefault("INGEST_BUCKET_PATH", "./data/test-uploads")
os.environ.setdefault("PROCESSED_TEXT_PATH", "./data/test-processed")
os.environ.setdefault("CLAIM_EXTRACTOR", "simple")

get_settings.cache_clear()

