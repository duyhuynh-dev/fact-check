"""Claim extraction service (MVP: sentence splitting, future: LLM-based)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sqlmodel import Session, delete, select

from backend.app.core.config import get_settings
from backend.app.db.models import Claim, Document
from backend.app.services.semantic_analysis import create_semantic_analyzer


@dataclass
class ClaimCandidate:
    """A candidate claim extracted from text."""

    text: str
    span_start: int | None = None
    span_end: int | None = None
    metadata: dict | None = None


class ClaimExtractor(Protocol):
    """Interface for claim extraction strategies."""

    def extract(self, text: str) -> list[ClaimCandidate]: ...


class SpacyClaimExtractor:
    """spaCy-based extractor that identifies factual claims using NLP."""

    def __init__(self):
        try:
            import spacy

            # Load spaCy model (download with: python -m spacy download en_core_web_sm)
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                # Fallback to blank model if not installed
                self.nlp = spacy.blank("en")
                self.nlp.add_pipe("sentencizer")
        except ImportError:
            raise ImportError(
                "spacy not installed. Install with: poetry add spacy && python -m spacy download en_core_web_sm"
            )
        
        # Initialize semantic analyzer for coded language detection
        try:
            self.semantic_analyzer = create_semantic_analyzer()
        except Exception:
            # Fallback if analyzer can't be created
            self.semantic_analyzer = None

    def extract(self, text: str) -> list[ClaimCandidate]:
        """Extract claims using spaCy NLP with semantic/conceptual analysis."""
        
        # For short texts (like tweets), keep as single claim with full context
        if len(text.strip()) < 500:
            # Run semantic analysis on full text
            semantic_analysis = None
            if self.semantic_analyzer:
                try:
                    semantic_analysis = self.semantic_analyzer.analyze(text.strip())
                except Exception:
                    pass
            
            metadata = {
                "strategy": "spacy_fulltext_short",
                "is_short_text": True,
            }
            
            if semantic_analysis:
                metadata["semantic_analysis"] = {
                    "is_antisemitic": semantic_analysis.is_antisemitic,
                    "confidence": semantic_analysis.confidence,
                    "detected_patterns": semantic_analysis.detected_patterns,
                    "coded_language_detected": semantic_analysis.coded_language_detected,
                    "implicit_meaning": semantic_analysis.implicit_meaning,
                }
            
            return [
                ClaimCandidate(
                    text=text.strip(),
                    span_start=0,
                    span_end=len(text),
                    metadata=metadata,
                )
            ]
        
        # For longer texts, use sentence-based extraction
        doc = self.nlp(text)
        
        # Get paragraph context for semantic analysis
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        
        # Build a simple map: for each sentence, find which paragraph it's in
        def get_paragraph_for_position(pos: int) -> str:
            """Find the paragraph containing a given character position."""
            current_pos = 0
            for para in paragraphs:
                para_start = current_pos
                para_end = current_pos + len(para)
                if para_start <= pos <= para_end:
                    return para
                current_pos = para_end + 2  # +2 for \n\n separator
            return paragraphs[0] if paragraphs else ""

        # Conspiracy theory indicators
        conspiracy_patterns = [
            "secret", "conspiracy", "plot", "control", "network", "shadow",
            "behind the scenes", "they", "them", "international", "global",
            "spying", "surveillance", "intrigue", "manipulate", "influence"
        ]
        
        # Antisemitic trope keywords
        antisemitic_keywords = [
            "zionist", "jewish", "jew", "israel", "holocaust", "protocols",
            "elders of zion", "world domination", "control banks", "control media"
        ]

        candidates: list[ClaimCandidate] = []
        for sent in doc.sents:
            sent_text = sent.text.strip()
            if len(sent_text) < 20:
                continue

            # Don't filter out exclamations - they might be threats
            # Only filter questions
            if sent_text.endswith("?"):
                continue

            sent_lower = sent_text.lower()
            
            # Detect conspiracy theory language
            has_conspiracy_language = any(pattern in sent_lower for pattern in conspiracy_patterns)
            has_antisemitic_keywords = any(keyword in sent_lower for keyword in antisemitic_keywords)
            
            # Look for factual indicators (dates, numbers, named entities)
            entities = list(sent.ents)
            has_entities = any(ent.label_ in ["PERSON", "ORG", "GPE", "DATE", "CARDINAL", "EVENT"] for ent in entities)
            has_verbs = any(token.pos_ == "VERB" for token in sent)
            
            # Check for claims about responsibility/blame (common in antisemitic rhetoric)
            has_responsibility_verbs = any(
                token.lemma_.lower() in ["bear", "responsible", "blame", "cause", "control", "influence"]
                for token in sent
            )
            
            # Check for threatening language
            threat_keywords = ["war", "threaten", "example", "show", "get you", "gone get"]
            has_threat_language = any(keyword in sent_lower for keyword in threat_keywords)

            # Get paragraph context for semantic analysis
            context = get_paragraph_for_position(sent.start_char)
            
            # Run semantic analysis for coded language detection
            # Skip for very long documents to speed up processing
            semantic_analysis = None
            if self.semantic_analyzer and len(text) < 50000:  # Skip semantic analysis for very long docs
                try:
                    # Use full paragraph context for better understanding
                    semantic_analysis = self.semantic_analyzer.analyze(sent_text, context=context)
                except Exception:
                    pass  # Continue without semantic analysis if it fails
            
            # Prioritize sentences that:
            # 1. Have entities/verbs (factual claims)
            # 2. Contain conspiracy language (important to fact-check)
            # 3. Contain antisemitic keywords (critical to verify)
            # 4. Make responsibility/blame claims
            # 5. Semantic analysis detects antisemitic content (even without keywords)
            # 6. Contain threatening language directed at groups
            has_semantic_antisemitism = (
                semantic_analysis and 
                semantic_analysis.is_antisemitic and 
                semantic_analysis.confidence > 0.5
            )
            
            if has_entities or has_verbs or has_conspiracy_language or has_antisemitic_keywords or has_responsibility_verbs or has_semantic_antisemitism or has_threat_language:
                # Calculate claim importance score
                importance = 0
                if has_entities:
                    importance += 1
                if has_verbs:
                    importance += 1
                if has_conspiracy_language:
                    importance += 2  # Higher weight for conspiracy claims
                if has_antisemitic_keywords:
                    importance += 3  # Highest weight for antisemitic content
                if has_responsibility_verbs:
                    importance += 1
                if has_semantic_antisemitism:
                    importance += 4  # Highest weight for semantically detected antisemitism
                if has_threat_language:
                    importance += 3  # High weight for threatening language
                
                metadata = {
                    "strategy": "spacy_nlp_enhanced",
                    "has_entities": has_entities,
                    "entity_count": len(entities),
                    "has_conspiracy_language": has_conspiracy_language,
                    "has_antisemitic_keywords": has_antisemitic_keywords,
                    "has_threat_language": has_threat_language,
                    "importance_score": importance,
                }
                
                # Add semantic analysis results
                if semantic_analysis:
                    metadata["semantic_analysis"] = {
                        "is_antisemitic": semantic_analysis.is_antisemitic,
                        "confidence": semantic_analysis.confidence,
                        "detected_patterns": semantic_analysis.detected_patterns,
                        "coded_language_detected": semantic_analysis.coded_language_detected,
                        "implicit_meaning": semantic_analysis.implicit_meaning,
                    }
                
                span_start = sent.start_char
                span_end = sent.end_char
                candidates.append(
                    ClaimCandidate(
                        text=sent_text,
                        span_start=span_start,
                        span_end=span_end,
                        metadata=metadata,
                    )
                )

        # Sort by importance score (most important claims first)
        candidates.sort(key=lambda x: x.metadata.get("importance_score", 0) if x.metadata else 0, reverse=True)

        # Fallback if no good candidates found
        if not candidates and text.strip():
            candidates.append(
                ClaimCandidate(
                    text=text.strip()[:500],  # Limit length
                    span_start=0,
                    span_end=min(len(text), 500),
                    metadata={"strategy": "spacy_fallback"},
                )
            )

        return candidates


class SimpleSentenceExtractor:
    """Lightweight extractor that splits text into sentences."""

    sentence_regex = re.compile(r"[^.!?]+[.!?]?", re.MULTILINE | re.DOTALL)

    def __init__(self, min_length: int = 20):
        self.min_length = min_length

    def extract(self, text: str) -> list[ClaimCandidate]:
        # For short texts, keep as single claim
        if len(text.strip()) < 500:
            return [
                ClaimCandidate(
                    text=text.strip(),
                    span_start=0,
                    span_end=len(text),
                    metadata={"strategy": "simple_fulltext_short"},
                )
            ]
        
        candidates: list[ClaimCandidate] = []
        for match in self.sentence_regex.finditer(text):
            sentence = match.group(0).strip()
            if len(sentence) < self.min_length:
                continue
            span_start, span_end = match.span()
            candidates.append(
                ClaimCandidate(
                    text=sentence,
                    span_start=span_start,
                    span_end=span_end,
                    metadata={"strategy": "simple_sentence_v1"},
                )
            )
        if not candidates and text.strip():
            candidates.append(
                ClaimCandidate(
                    text=text.strip(),
                    span_start=0,
                    span_end=len(text),
                    metadata={"strategy": "fallback_fulltext"},
                )
            )
        return candidates


class ClaimService:
    """Coordinates reading document text and persisting extracted claims."""

    def __init__(self, extractor: ClaimExtractor | None = None):
        if extractor is not None:
            self.extractor = extractor
        else:
            settings = get_settings()
            if settings.claim_extractor == "llm":
                self.extractor = LLMClaimExtractor(
                    model=settings.openai_model,
                    api_key=settings.openai_api_key,
                )
            elif settings.claim_extractor == "spacy":
                self.extractor = SpacyClaimExtractor()
            else:
                self.extractor = SimpleSentenceExtractor()

    def extract_for_document(self, session: Session, document: Document) -> list[Claim]:
        if not document.text_path:
            raise ValueError("Document has no normalized text available for claim extraction.")
        text_path = Path(document.text_path)
        text = text_path.read_text(encoding="utf-8")

        session.exec(delete(Claim).where(Claim.document_id == document.id))

        candidates = self.extractor.extract(text)
        persisted: list[Claim] = []
        for candidate in candidates:
            claim = Claim(
                document_id=document.id,
                text=candidate.text,
                span_start=candidate.span_start,
                span_end=candidate.span_end,
                metadata_json=candidate.metadata,
            )
            session.add(claim)
            persisted.append(claim)
        session.commit()
        for claim in persisted:
            session.refresh(claim)
        return persisted


class LLMClaimExtractor:
    """LLM-backed extractor using OpenAI responses."""

    def __init__(self, model: str, api_key: str | None):
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY required for LLM extractor")
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def extract(self, text: str) -> list[ClaimCandidate]:
        # For short texts, keep as single claim and analyze with LLM
        if len(text.strip()) < 500:
            prompt = """Analyze this text for antisemitic content, factual claims, or problematic statements. 
            If it's antisemitic, threatening, or uses stereotypes, identify it as such.
            Return JSON with: {"is_antisemitic": boolean, "is_factual_claim": boolean, "explanation": string}"""
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert in detecting antisemitic content and factual claims."},
                        {"role": "user", "content": text[:2000]},
                    ],
                )
                # Parse response if needed
            except Exception:
                pass
            
            return [
                ClaimCandidate(
                    text=text.strip(),
                    span_start=0,
                    span_end=len(text),
                    metadata={"strategy": "llm_fulltext_short"},
                )
            ]
        
        prompt = (
            "Extract factual claims from the provided text. "
            "Return JSON array with objects: "
            "{\"text\": str, \"span_start\": int|null, \"span_end\": int|null}."
            "Be concise; split long paragraphs into atomic claims."
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": prompt,
                },
                {
                    "role": "user",
                    "content": text[:8000],
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "claims",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "claims": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "text": {"type": "string"},
                                        "span_start": {"type": ["integer", "null"]},
                                        "span_end": {"type": ["integer", "null"]},
                                        "confidence": {"type": ["number", "null"]},
                                    },
                                    "required": ["text"],
                                },
                            }
                        },
                        "required": ["claims"],
                    },
                },
            },
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        candidates: list[ClaimCandidate] = []
        for entry in data.get("claims", []):
            candidates.append(
                ClaimCandidate(
                    text=entry.get("text", "").strip(),
                    span_start=entry.get("span_start"),
                    span_end=entry.get("span_end"),
                    metadata={
                        "strategy": "llm_openai",
                        "confidence": entry.get("confidence"),
                        "model": self.model,
                    },
                )
            )
        return candidates
