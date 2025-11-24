"""Claim extraction services."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sqlmodel import Session, delete

from backend.app.core.config import get_settings
from backend.app.db.models import Claim, Document


@dataclass
class ClaimCandidate:
    text: str
    span_start: int | None = None
    span_end: int | None = None
    metadata: dict | None = None


class ClaimExtractor(Protocol):
    """Extractor interface."""

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

    def extract(self, text: str) -> list[ClaimCandidate]:
        """Extract claims using spaCy NLP."""
        doc = self.nlp(text)

        candidates: list[ClaimCandidate] = []
        for sent in doc.sents:
            sent_text = sent.text.strip()
            if len(sent_text) < 20:
                continue

            # Filter for factual statements (not questions, exclamations)
            if sent_text.endswith("?") or sent_text.endswith("!"):
                continue

            # Look for factual indicators (dates, numbers, named entities)
            has_entities = any(ent.label_ in ["PERSON", "ORG", "GPE", "DATE", "CARDINAL"] for ent in sent.ents)
            has_verbs = any(token.pos_ == "VERB" for token in sent)

            # Prioritize sentences with entities and verbs (more likely to be factual claims)
            if has_entities or has_verbs:
                span_start = sent.start_char
                span_end = sent.end_char
                candidates.append(
                    ClaimCandidate(
                        text=sent_text,
                        span_start=span_start,
                        span_end=span_end,
                        metadata={
                            "strategy": "spacy_nlp",
                            "has_entities": has_entities,
                            "entity_count": len(list(sent.ents)),
                        },
                    )
                )

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

