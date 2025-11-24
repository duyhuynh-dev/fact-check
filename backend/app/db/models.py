"""SQLModel definitions for documents, claims, and evidence records."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, JSON, String
from sqlmodel import Field, Relationship, SQLModel


class TimestampMixin(SQLModel):
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow},
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


class Document(DocumentBase, TimestampMixin, table=True):
    __tablename__ = "documents"

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        primary_key=True,
        index=True,
        sa_column=Column(String, unique=True),
    )

    claims: list["Claim"] = Relationship(back_populates="document")


class ClaimBase(SQLModel):
    text: str = Field(description="Claim text extracted from the document.")
    span_start: int | None = Field(default=None)
    span_end: int | None = Field(default=None)
    verdict: str | None = Field(
        default=None,
        description="supported | partial | contradicted | no_evidence",
        max_length=32,
    )
    rationale: str | None = Field(default=None)
    score: float | None = Field(default=None)
    embedding: Optional[list[float]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Optional dense embedding stored as JSON until pgvector is wired.",
    )


class Claim(ClaimBase, TimestampMixin, table=True):
    __tablename__ = "claims"

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        primary_key=True,
        index=True,
        sa_column=Column(String, unique=True),
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
    source_uri: str | None = Field(default=None)
    snippet: str = Field(description="Relevant excerpt supporting or refuting the claim.")
    verdict_contribution: str = Field(
        description="supports | refutes | neutral",
        max_length=32,
    )
    metadata_json: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional structured metadata (page, paragraph, etc.).",
    )


class Evidence(EvidenceBase, TimestampMixin, table=True):
    __tablename__ = "evidence"

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        primary_key=True,
        index=True,
        sa_column=Column(String, unique=True),
    )
    claim_id: str = Field(
        foreign_key="claims.id",
        nullable=False,
        description="FK to associated claim.",
    )

    claim: Claim = Relationship(back_populates="evidence")

