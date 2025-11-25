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
        from backend.app.core.config import get_settings
        from backend.app.services.content_classifier import create_content_classifier
        from backend.app.services.semantic_analysis import create_semantic_analyzer
        
        settings = get_settings()
        
        # FIRST: Run semantic analysis if not already done (fallback)
        semantic_analysis_result = None
        if claim.metadata_json and "semantic_analysis" in claim.metadata_json:
            sem_data = claim.metadata_json["semantic_analysis"]
            from backend.app.services.semantic_analysis import SemanticAnalysis
            semantic_analysis_result = SemanticAnalysis(
                is_antisemitic=sem_data.get('is_antisemitic', False),
                confidence=sem_data.get('confidence', 0.0),
                detected_patterns=sem_data.get('detected_patterns', []),
                explanation=sem_data.get('explanation', ''),
                coded_language_detected=sem_data.get('coded_language_detected', False),
                implicit_meaning=sem_data.get('implicit_meaning'),
            )
        else:
            # Run semantic analysis now if not in metadata
            try:
                analyzer = create_semantic_analyzer()
                semantic_analysis_result = analyzer.analyze(claim.text)
                if claim.metadata_json is None:
                    claim.metadata_json = {}
                claim.metadata_json["semantic_analysis"] = {
                    "is_antisemitic": semantic_analysis_result.is_antisemitic,
                    "confidence": semantic_analysis_result.confidence,
                    "detected_patterns": semantic_analysis_result.detected_patterns,
                    "explanation": semantic_analysis_result.explanation,
                    "coded_language_detected": semantic_analysis_result.coded_language_detected,
                    "implicit_meaning": semantic_analysis_result.implicit_meaning,
                }
            except Exception:
                pass
        
        # Check for antisemitic tropes FIRST (before religious content check)
        if semantic_analysis_result and semantic_analysis_result.is_antisemitic and semantic_analysis_result.confidence > 0.6:
            patterns = semantic_analysis_result.detected_patterns
            claim.verdict = "antisemitic_trope"
            rationale_parts = [
                f"This content uses antisemitic tropes or stereotypes.",
                f"Detected patterns: {', '.join(patterns) if patterns else 'antisemitic content'}.",
                semantic_analysis_result.explanation or "Content contains antisemitic messaging.",
            ]
            if semantic_analysis_result.implicit_meaning:
                rationale_parts.append(f"Implicit meaning: {semantic_analysis_result.implicit_meaning}")
            claim.rationale = " ".join([p for p in rationale_parts if p])
            claim.score = None
            if claim.metadata_json is None:
                claim.metadata_json = {}
            claim.metadata_json["antisemitic_trope_detected"] = True
            claim.metadata_json["trope_patterns"] = patterns
            session.add(claim)
            session.commit()
            session.refresh(claim)
            return claim
        
        # Check if claim is from religious/mythological content
        classifier = create_content_classifier()
        classification = classifier.classify(claim.text)
        
        # If it's religious or mythological content, mark as not applicable
        # BUT note that religious texts are legitimate sources for learning about Judaism
        if classification.is_religious_text or classification.is_mythological:
            rationale = f"This appears to be {classification.content_type} content, not a factual claim to verify. {classification.explanation}"
            
            # Add context about legitimate sources
            if classification.is_religious_text:
                rationale += " Note: Religious texts like the Torah and Talmud are legitimate and essential sources for learning about Judaism, Jewish beliefs, and Jewish practices. However, they are sacred texts, not historical documents to be fact-checked as events."
            
            claim.verdict = "not_applicable"
            claim.rationale = rationale
            claim.score = None
            if claim.metadata_json is None:
                claim.metadata_json = {}
            claim.metadata_json["content_classification"] = {
                "content_type": classification.content_type,
                "is_religious": classification.is_religious_text,
                "is_mythological": classification.is_mythological,
                "confidence": classification.confidence,
                "note": "Religious texts are legitimate sources for understanding Judaism, but not for historical fact-checking"
            }
            session.add(claim)
            session.commit()
            session.refresh(claim)
            return claim
        
        evidence = self.evidence_retriever.retrieve(
            claim.text, 
            limit=settings.evidence_retrieval_limit,
            min_similarity=settings.evidence_min_similarity
        )

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

