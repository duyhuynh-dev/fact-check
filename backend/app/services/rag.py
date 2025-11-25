"""RAG (Retrieval-Augmented Generation) service for evidence retrieval (MVP)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
from openai import OpenAI

from backend.app.core.config import get_settings


@dataclass
class EvidenceSnippet:
    """Evidence snippet for verification."""

    source_name: str
    snippet: str
    source_uri: str | None = None
    citation: str | None = None
    author: str | None = None
    reliability_score: float | None = None


@dataclass
class DocumentChunk:
    """A chunk of text with its embedding."""

    text: str
    source_name: str
    source_uri: str | None = None
    metadata: dict | None = None
    embedding: list[float] | None = None


class VectorStore(Protocol):
    """Interface for vector storage and retrieval."""

    def add(self, chunk: DocumentChunk) -> None: ...
    def search(self, query_embedding: list[float], limit: int = 5) -> list[DocumentChunk]: ...


class InMemoryVectorStore:
    """Simple in-memory vector store (MVP)."""

    def __init__(self):
        self.chunks: list[DocumentChunk] = []

    def add(self, chunk: DocumentChunk) -> None:
        self.chunks.append(chunk)

    def search(self, query_embedding: list[float], query_text: str = "", limit: int = 5, min_similarity: float = 0.3) -> list[DocumentChunk]:
        """Hybrid search: semantic (embedding) + keyword matching."""
        if not self.chunks:
            return []

        # Filter chunks with embeddings
        chunks_with_embeddings = [c for c in self.chunks if c.embedding]
        if not chunks_with_embeddings:
            return []

        query_vec = np.array(query_embedding)
        query_lower = query_text.lower()
        query_keywords = set(query_lower.split())

        # Compute hybrid scores (semantic + keyword)
        scored_chunks = []
        for chunk in chunks_with_embeddings:
            chunk_vec = np.array(chunk.embedding)
            
            # Semantic similarity (0-1)
            semantic_score = np.dot(query_vec, chunk_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(chunk_vec)
            )
            
            # Keyword matching boost
            chunk_lower = chunk.text.lower()
            chunk_keywords = set(chunk_lower.split())
            keyword_overlap = len(query_keywords & chunk_keywords) / max(len(query_keywords), 1)
            keyword_boost = min(keyword_overlap * 0.2, 0.2)  # Max 0.2 boost
            
            # Combined score
            combined_score = semantic_score + keyword_boost
            
            if combined_score >= min_similarity:
                scored_chunks.append((combined_score, semantic_score, chunk))

        # Sort by combined score, then by semantic score
        scored_chunks.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [chunk for _, _, chunk in scored_chunks[:limit]]


class EmbeddingService:
    """Service for generating embeddings. Supports OpenAI API or free local models."""

    def __init__(self, api_key: str | None = None, model: str = "text-embedding-3-small", use_free: bool = False):
        self.use_free = use_free
        if use_free:
            # Use free local embeddings (sentence-transformers)
            try:
                from sentence_transformers import SentenceTransformer
                self.local_model = SentenceTransformer("all-MiniLM-L6-v2")
                self.model = "all-MiniLM-L6-v2"
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. Install with: poetry add sentence-transformers"
                )
        else:
            settings = get_settings()
            if not (api_key or settings.openai_api_key):
                # Fallback to free if no API key
                try:
                    from sentence_transformers import SentenceTransformer
                    self.local_model = SentenceTransformer("all-MiniLM-L6-v2")
                    self.model = "all-MiniLM-L6-v2"
                    self.use_free = True
                except ImportError:
                    raise RuntimeError(
                        "No OpenAI API key and sentence-transformers not installed. "
                        "Either set OPENAI_API_KEY or install: poetry add sentence-transformers"
                    )
            else:
                self.client = OpenAI(api_key=api_key or settings.openai_api_key)
                self.model = model

    def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        if self.use_free:
            return self.local_model.encode(text, convert_to_numpy=True).tolist()
        else:
            response = self.client.embeddings.create(model=self.model, input=text)
            return response.data[0].embedding


class EvidenceRetriever:
    """RAG-based evidence retriever."""

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        embedding_service: EmbeddingService | None = None,
        use_free_embeddings: bool | None = None,
    ):
        self.vector_store = vector_store or InMemoryVectorStore()
        settings = get_settings()
        # Use free embeddings if no API key or explicitly requested
        use_free = use_free_embeddings if use_free_embeddings is not None else (not settings.openai_api_key)
        self.embedding_service = embedding_service or EmbeddingService(
            api_key=settings.openai_api_key,
            use_free=use_free,
        )

    def retrieve(self, claim_text: str, limit: int = 5, min_similarity: float = 0.3) -> list[EvidenceSnippet]:
        """Retrieve relevant evidence for a claim using hybrid search."""
        if not self.vector_store.chunks:
            return []  # No evidence loaded yet

        query_embedding = self.embedding_service.embed(claim_text)
        chunks = self.vector_store.search(
            query_embedding, 
            query_text=claim_text, 
            limit=limit,
            min_similarity=min_similarity
        )

        return [
            EvidenceSnippet(
                source_name=chunk.source_name,
                snippet=chunk.text,
                source_uri=chunk.source_uri,
                citation=chunk.metadata.get("citation") if chunk.metadata else None,
                author=chunk.metadata.get("author") if chunk.metadata else None,
                reliability_score=chunk.metadata.get("reliability_score") if chunk.metadata else None,
            )
            for chunk in chunks
        ]

    def load_from_file(self, file_path: Path, source_name: str) -> None:
        """Load evidence from a text file with improved chunking strategy."""
        text = file_path.read_text(encoding="utf-8")
        
        # Improved chunking: split by paragraphs, but also handle long paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        
        chunks_created = 0
        for para in paragraphs:
            if len(para) < 50:  # Skip very short paragraphs
                continue
            
            # For longer paragraphs, split into sentences and create overlapping chunks
            if len(para) > 500:
                # Split into sentences and create overlapping windows
                sentences = para.split('. ')
                window_size = 3  # 3 sentences per chunk
                overlap = 1  # 1 sentence overlap
                
                for i in range(0, len(sentences), window_size - overlap):
                    chunk_text = '. '.join(sentences[i:i + window_size])
                    if len(chunk_text.strip()) < 50:
                        continue
                    if not chunk_text.endswith('.'):
                        chunk_text += '.'
                    
                    embedding = self.embedding_service.embed(chunk_text)
                    # Extract source metadata from filename or default
                    metadata = {
                        "chunk_type": "sentence_window",
                        "chunk_index": chunks_created,
                        "reliability_score": 0.8,  # Default reliability for loaded evidence
                    }
                    # Try to infer author/source from filename
                    if "adl" in source_name.lower():
                        metadata["author"] = "Anti-Defamation League"
                        metadata["reliability_score"] = 0.9
                    elif "encyclopedia" in source_name.lower() or "holocaust" in source_name.lower():
                        metadata["reliability_score"] = 0.95
                    
                    chunk = DocumentChunk(
                        text=chunk_text.strip(),
                        source_name=source_name,
                        source_uri=str(file_path),
                        embedding=embedding,
                        metadata=metadata
                    )
                    self.vector_store.add(chunk)
                    chunks_created += 1
            else:
                # Use paragraph as-is for shorter paragraphs
                embedding = self.embedding_service.embed(para)
                
                # Extract source metadata
                metadata = {
                    "chunk_type": "paragraph",
                    "chunk_index": chunks_created,
                    "reliability_score": 0.8,
                }
                if "adl" in source_name.lower():
                    metadata["author"] = "Anti-Defamation League"
                    metadata["reliability_score"] = 0.9
                elif "encyclopedia" in source_name.lower() or "holocaust" in source_name.lower():
                    metadata["reliability_score"] = 0.95
                
                chunk = DocumentChunk(
                    text=para,
                    source_name=source_name,
                    source_uri=str(file_path),
                    embedding=embedding,
                    metadata=metadata
                )
                self.vector_store.add(chunk)
                chunks_created += 1


def create_default_evidence_retriever() -> EvidenceRetriever:
    """Factory for default evidence retriever."""
    return EvidenceRetriever()

