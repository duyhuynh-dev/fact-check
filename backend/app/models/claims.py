"""Schemas for claim responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ClaimRead(BaseModel):
    id: str
    document_id: str
    text: str
    span_start: Optional[int]
    span_end: Optional[int]
    verdict: Optional[str]
    score: Optional[float]
    metadata_json: Optional[dict]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClaimList(BaseModel):
    items: list[ClaimRead]

