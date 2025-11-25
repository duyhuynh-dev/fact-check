"""Schemas for document ingestion endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentBase(BaseModel):
    title: Optional[str] = Field(default=None, max_length=512)
    source_type: str = Field(default="upload", max_length=64)


class DocumentRead(DocumentBase):
    id: str
    ingest_status: str
    ingest_failure_reason: Optional[str]
    raw_path: str
    text_path: Optional[str]
    ingest_progress: Optional[float] = None
    ingest_progress_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentList(BaseModel):
    items: list[DocumentRead]

