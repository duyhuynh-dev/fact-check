"""Schemas for document verification results and scoring."""

from pydantic import BaseModel, Field


class VerdictSummary(BaseModel):
    """Summary of verdict counts."""

    supported: int = Field(default=0, description="Number of supported claims")
    partial: int = Field(default=0, description="Number of partially supported claims")
    contradicted: int = Field(default=0, description="Number of contradicted claims")
    no_evidence: int = Field(default=0, description="Number of claims with no evidence")
    not_applicable: int = Field(default=0, description="Number of claims that are not factual (e.g., religious texts)")
    antisemitic_trope: int = Field(default=0, description="Number of claims using antisemitic tropes or stereotypes")
    unverified: int = Field(default=0, description="Number of claims not yet verified")


class DocumentResults(BaseModel):
    """Aggregated results for a document."""

    document_id: str
    total_claims: int = Field(description="Total number of claims extracted")
    verified_claims: int = Field(description="Number of claims that have been verified")
    overall_score: float | None = Field(
        default=None,
        description="Overall document score (0-100), average of claim scores",
    )
    verdict_summary: VerdictSummary = Field(description="Breakdown of verdicts")
    risk_level: str = Field(
        description="Overall risk level: 'low', 'medium', 'high', or 'unknown'"
    )

