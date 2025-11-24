"""Claim verification service (MVP: LLM-based verdict generation)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from sqlmodel import Session

from backend.app.core.config import get_settings
from backend.app.db.models import Claim
from backend.app.services.rag import (
    EvidenceRetriever,
    EvidenceSnippet,
    create_default_evidence_retriever,
)


def create_verifier():
    """Factory that returns appropriate verifier based on settings."""
    settings = get_settings()

    # Priority: free_mode > verification_provider > fallback
    if settings.free_mode:
        from backend.app.services.verification_free import FreeClaimVerifier

        return FreeClaimVerifier()

    if settings.verification_provider == "gemini":
        if settings.gemini_api_key:
            from backend.app.services.verification_gemini import GeminiClaimVerifier

            return GeminiClaimVerifier()
        else:
            # Fallback to free if no Gemini key
            from backend.app.services.verification_free import FreeClaimVerifier

            return FreeClaimVerifier()

    if settings.verification_provider == "openai":
        if settings.openai_api_key:
            return ClaimVerifier()
        else:
            # Fallback to free if no OpenAI key
            from backend.app.services.verification_free import FreeClaimVerifier

            return FreeClaimVerifier()

    # Default: try Gemini first (free tier), then free mode
    if settings.gemini_api_key:
        from backend.app.services.verification_gemini import GeminiClaimVerifier

        return GeminiClaimVerifier()
    else:
        from backend.app.services.verification_free import FreeClaimVerifier

        return FreeClaimVerifier()


class ClaimVerifier:
    """Verifies claims against evidence using LLM."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        evidence_retriever: EvidenceRetriever | None = None,
    ):
        settings = get_settings()
        self.model = model or settings.openai_model
        self.api_key = api_key or settings.openai_api_key
        self.evidence_retriever = evidence_retriever or create_default_evidence_retriever()

        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY required for verification")

        from openai import OpenAI

        self.client = OpenAI(api_key=self.api_key)

    def verify(self, claim: Claim, session: Session) -> Claim:
        """Verify a claim and update it with verdict/rationale/score."""
        evidence = self.evidence_retriever.retrieve(claim.text, limit=5)

        prompt = self._build_prompt(claim.text, evidence)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a fact-checker specializing in antisemitism-related content."},
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "verdict",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "verdict": {
                                "type": "string",
                                "enum": ["supported", "partial", "contradicted", "no_evidence"],
                            },
                            "rationale": {"type": "string"},
                            "score": {"type": "number", "minimum": 0, "maximum": 100},
                        },
                        "required": ["verdict", "rationale", "score"],
                    },
                },
            },
        )

        content = response.choices[0].message.content
        data = json.loads(content or "{}")

        claim.verdict = data.get("verdict")
        claim.rationale = data.get("rationale")
        claim.score = data.get("score")
        if claim.metadata_json is None:
            claim.metadata_json = {}
        claim.metadata_json["verification_model"] = self.model
        claim.metadata_json["evidence_count"] = len(evidence)

        session.add(claim)
        session.commit()
        session.refresh(claim)
        return claim

    def _build_prompt(self, claim_text: str, evidence: list[EvidenceSnippet]) -> str:
        """Build verification prompt."""
        evidence_text = "\n\n".join(
            [f"[{e.source_name}]: {e.snippet}" for e in evidence]
        ) if evidence else "No evidence retrieved."

        return f"""Verify the following claim about antisemitism or Jewish history:

CLAIM: {claim_text}

EVIDENCE:
{evidence_text}

Return JSON with:
- verdict: "supported" | "partial" | "contradicted" | "no_evidence"
- rationale: brief explanation
- score: 0-100 (100 = fully supported, 0 = contradicted, 50 = no evidence)
"""

