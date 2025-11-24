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

    def search(self, query_embedding: list[float], limit: int = 5) -> list[DocumentChunk]:
        """Cosine similarity search."""
        if not self.chunks:
            return []

        # Filter chunks with embeddings
        chunks_with_embeddings = [c for c in self.chunks if c.embedding]
        if not chunks_with_embeddings:
            return []

        # Compute cosine similarities
        query_vec = np.array(query_embedding)
        similarities = []
        for chunk in chunks_with_embeddings:
            chunk_vec = np.array(chunk.embedding)
            similarity = np.dot(query_vec, chunk_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(chunk_vec)
            )
            similarities.append((similarity, chunk))

        # Sort by similarity and return top-k
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in similarities[:limit]]


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

    def retrieve(self, claim_text: str, limit: int = 5) -> list[EvidenceSnippet]:
        """Retrieve relevant evidence for a claim."""
        if not self.vector_store.chunks:
            return []  # No evidence loaded yet

        query_embedding = self.embedding_service.embed(claim_text)
        chunks = self.vector_store.search(query_embedding, limit=limit)

        return [
            EvidenceSnippet(
                source_name=chunk.source_name,
                snippet=chunk.text,
                source_uri=chunk.source_uri,
            )
            for chunk in chunks
        ]

    def load_from_file(self, file_path: Path, source_name: str) -> None:
        """Load evidence from a text file (MVP: simple chunking)."""
        text = file_path.read_text(encoding="utf-8")
        # Simple chunking: split by paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        for para in paragraphs:
            if len(para) < 50:  # Skip very short paragraphs
                continue

            embedding = self.embedding_service.embed(para)
            chunk = DocumentChunk(
                text=para,
                source_name=source_name,
                source_uri=str(file_path),
                embedding=embedding,
            )
            self.vector_store.add(chunk)


def create_default_evidence_retriever() -> EvidenceRetriever:
    """Factory for default evidence retriever."""
    return EvidenceRetriever()

