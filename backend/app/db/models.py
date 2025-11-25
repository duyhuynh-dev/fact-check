"""SQLModel definitions for documents, claims, and evidence records."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, JSON, String
from sqlmodel import Field, Relationship, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin(SQLModel):
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(
        default_factory=utc_now,
        nullable=False,
        sa_column_kwargs={"onupdate": utc_now},
    )


class DocumentBase(SQLModel):
    title: str | None = Field(default=None, max_length=512)
    source_type: str = Field(
        default="upload", description="upload | url | transcript | generated"
    )
    raw_path: str = Field(
        description="Filesystem or object storage path for the original artifact."
    )
    text_path: str | None = Field(
        default=None,
        description="Path to normalized text blob ready for claim extraction.",
    )
    ingest_status: str = Field(
        default="pending",
        description="pending | processing | succeeded | failed",
        max_length=32,
    )
    ingest_failure_reason: str | None = Field(default=None)
    ingest_progress: float | None = Field(
        default=None,
        description="Processing progress (0.0-1.0)",
    )
    ingest_progress_message: str | None = Field(
        default=None,
        description="Current processing stage message",
    )


class Document(DocumentBase, TimestampMixin, table=True):
    __tablename__ = "documents"

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        sa_column=Column(String, primary_key=True, unique=True, index=True),
    )

    claims: list["Claim"] = Relationship(back_populates="document")


class ClaimBase(SQLModel):
    text: str = Field(description="Claim text extracted from the document.")
    span_start: int | None = Field(default=None)
    span_end: int | None = Field(default=None)
    verdict: str | None = Field(
        default=None,
        description="supported | partial | contradicted | no_evidence | not_applicable | antisemitic_trope",
        max_length=32,
    )
    rationale: str | None = Field(default=None)
    score: float | None = Field(default=None)
    embedding: Optional[list[float]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Optional dense embedding stored as JSON until pgvector is wired.",
    )
    metadata_json: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Extractor metadata such as prompt version or confidence.",
    )


class Claim(ClaimBase, TimestampMixin, table=True):
    __tablename__ = "claims"

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        sa_column=Column(String, primary_key=True, unique=True, index=True),
    )
    document_id: str = Field(
        foreign_key="documents.id",
        nullable=False,
        description="FK to parent document.",
    )

    document: Document = Relationship(back_populates="claims")
    evidence: list["Evidence"] = Relationship(back_populates="claim")


class EvidenceBase(SQLModel):
    source_name: str = Field(description="Dataset or publication name.")
    source_uri: str | None = Field(default=None, description="URL or citation to original source.")
    snippet: str = Field(description="Relevant excerpt supporting or refuting the claim.")
    verdict_contribution: str = Field(
        description="supports | refutes | neutral",
        max_length=32,
    )
    citation: str | None = Field(
        default=None,
        description="Formal citation (e.g., 'ADL Report 2023, p. 45')",
    )
    author: str | None = Field(default=None, description="Author or organization of source.")
    publication_date: str | None = Field(default=None, description="Publication date if known.")
    reliability_score: float | None = Field(
        default=None,
        description="Source reliability score (0-1), based on source type and verification.",
    )
    metadata_json: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional structured metadata (page, paragraph, topic tags, etc.).",
    )


class Evidence(EvidenceBase, TimestampMixin, table=True):
    __tablename__ = "evidence"

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        sa_column=Column(String, primary_key=True, unique=True, index=True),
    )
    claim_id: str = Field(
        foreign_key="claims.id",
        nullable=False,
        description="FK to associated claim.",
    )

    claim: Claim = Relationship(back_populates="evidence")

