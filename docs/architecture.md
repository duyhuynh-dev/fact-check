# Architecture Overview

## Stack Choices

- **Language**: Python 3.11 for rich ML/NLP ecosystem.
- **API framework**: FastAPI for async IO, OpenAPI docs, and easy deployment.
- **Storage**:
  - PostgreSQL (with `pgvector`) for ingestion metadata, claim/evidence tracking.
  - Object storage (local `data/` in dev, S3-compatible in prod) for raw documents.
  - Vector store abstraction (start with local Chroma, upgrade to managed pgvector).
- **ML/RAG tooling**:
  - OCR: `pytesseract` + `rapidocr-onnxruntime` fallback for multilingual text.
  - Claim extraction & verification: LLM orchestration through LangChain/LlamaIndex.
  - Embeddings: default to OpenAI text-embedding-3-large; add local fallback later.

## Service Layout

```
backend/
  app/
    main.py          # FastAPI entrypoint
    core/            # settings, logging, feature flags
    db/              # sqlmodel metadata + migrations
    routes/          # versioned API routers
    services/        # ingestion, retrieval, verification modules
    models/          # pydantic request/response schemas
```

## Data Flow (MVP)

1. **Upload**: `/v1/documents` accepts PDF/image/text; stores artifact in `data/` and records metadata.
2. **Preprocess**: OCR/clean text, segment sentences, enqueue claim extraction job.
3. **Claim Extraction**: LLM prompt extracts structured claims with spans; store in DB.

### Claim Extraction Notes

- `backend/app/services/claims.py` contains `ClaimService` with pluggable extractors (currently `SimpleSentenceExtractor`).
- Ingestion worker triggers extraction after OCR; API exposes `/v1/documents/{id}/claims` and re-run endpoint.
- Claims stored in `claims` table with spans, metadata, and verdict placeholders for future verification.

4. **Evidence Retrieval**: For each claim, embed and query vector store; cache passages + citations.
5. **Verification**: LLM compares claim vs evidence, emits verdict, rationale, confidence score.
6. **Reporting**: `/v1/reports/{doc_id}` returns per-claim verdicts + aggregated score.

### Persistence Notes

- SQLModel tables: `Document`, `Claim`, `Evidence` (`backend/app/db/models.py`).
- `backend/app/db/session.py` exposes `init_db()` (startup) + `get_session()` (FastAPI dependency).
- Storage layout: raw artifacts under `Settings.ingest_bucket_path`, normalized text under `Settings.processed_text_path`.
- Embeddings temporarily stored as JSON arrays until pgvector migrations land.

## Future Components

- Streaming ingestion pipeline (Celery or Arq) for large docs.
- Admin console for reviewers to approve/override machine verdicts.
- Dataset refresh jobs to keep knowledge base current.
