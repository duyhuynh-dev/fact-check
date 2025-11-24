"""Gemini API-based verification service (free tier available)."""

from __future__ import annotations

import json
from sqlmodel import Session

from backend.app.core.config import get_settings
from backend.app.db.models import Claim
from backend.app.services.rag import EvidenceRetriever, create_default_evidence_retriever


class GeminiClaimVerifier:
    """Verifies claims using Google Gemini API (free tier available)."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        evidence_retriever: EvidenceRetriever | None = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.evidence_retriever = evidence_retriever or create_default_evidence_retriever()

        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY required for Gemini verification")

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
        except ImportError:
            raise ImportError(
                "google-generativeai not installed. Install with: poetry add google-generativeai"
            )

    def verify(self, claim: Claim, session: Session) -> Claim:
        """Verify a claim against evidence using Gemini."""
        evidence = self.evidence_retriever.retrieve(claim.text, limit=5)

        # Build prompt for Gemini
        evidence_text = "\n\n".join(
            [f"[{e.source_name}]: {e.snippet}" for e in evidence]
        ) if evidence else "No evidence retrieved from knowledge base."

        prompt = f"""You are a fact-checker specializing in antisemitism and Jewish history.

TASK: Verify the following claim based ONLY on the provided evidence.

CLAIM TO VERIFY:
{claim.text}

EVIDENCE FROM KNOWLEDGE BASE:
{evidence_text}

INSTRUCTIONS:
1. If the evidence clearly supports the claim, respond with verdict: "supported"
2. If the evidence partially supports the claim, respond with verdict: "partial"
3. If the evidence contradicts the claim, respond with verdict: "contradicted"
4. If there is no relevant evidence, respond with verdict: "no_evidence"

Provide your response as JSON with these exact fields:
{{
  "verdict": "supported" | "partial" | "contradicted" | "no_evidence",
  "rationale": "brief explanation of your reasoning",
  "score": <number between 0-100, where 100=fully supported, 0=contradicted, 50=no evidence>
}}
"""

        try:
            response = self.client.generate_content(prompt)
            content = response.text.strip()

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            claim.verdict = data.get("verdict")
            claim.rationale = data.get("rationale")
            claim.score = data.get("score")
            if claim.metadata_json is None:
                claim.metadata_json = {}
            claim.metadata_json["verification_model"] = self.model
            claim.metadata_json["verification_provider"] = "gemini"
            claim.metadata_json["evidence_count"] = len(evidence)

        except Exception as e:
            # Fallback to no_evidence if verification fails
            claim.verdict = "no_evidence"
            claim.rationale = f"Verification failed: {str(e)}"
            claim.score = 50.0
            if claim.metadata_json is None:
                claim.metadata_json = {}
            claim.metadata_json["verification_error"] = str(e)

        session.add(claim)
        session.commit()
        session.refresh(claim)
        return claim

