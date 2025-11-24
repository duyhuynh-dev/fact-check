"""Free/development verification service (no API costs)."""

from __future__ import annotations

import random
from sqlmodel import Session

from backend.app.db.models import Claim
from backend.app.services.rag import EvidenceRetriever, EvidenceSnippet


class FreeClaimVerifier:
    """Mock verification service for development/testing (no API costs)."""

    def __init__(self, evidence_retriever: EvidenceRetriever | None = None):
        from backend.app.services.rag import create_default_evidence_retriever

        self.evidence_retriever = evidence_retriever or create_default_evidence_retriever()

    def verify(self, claim: Claim, session: Session) -> Claim:
        """Mock verification that simulates verdicts based on evidence."""
        evidence = self.evidence_retriever.retrieve(claim.text, limit=5)

        # Simple heuristic: if evidence found, likely supported
        if evidence:
            # More evidence = higher confidence
            score = min(70 + len(evidence) * 5, 95)
            verdict = "supported" if score > 80 else "partial"
            rationale = f"Found {len(evidence)} relevant evidence snippet(s) supporting this claim."
        else:
            # No evidence = no_evidence verdict
            score = 50.0
            verdict = "no_evidence"
            rationale = "No evidence found in knowledge base to verify this claim."

        # Add some randomness for demo purposes
        if random.random() < 0.1:  # 10% chance of contradicted
            verdict = "contradicted"
            score = random.uniform(20, 40)
            rationale = "Evidence suggests this claim may be contradicted."

        claim.verdict = verdict
        claim.rationale = rationale
        claim.score = round(score, 2)
        if claim.metadata_json is None:
            claim.metadata_json = {}
        claim.metadata_json["verification_model"] = "free_mock_v1"
        claim.metadata_json["evidence_count"] = len(evidence)

        session.add(claim)
        session.commit()
        session.refresh(claim)
        return claim

