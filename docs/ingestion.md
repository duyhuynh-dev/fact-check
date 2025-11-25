# Ingestion & OCR Plan

## Goals

- Accept PDFs, images, and plain-text uploads related to antisemitism topics.
- Normalize raw artifacts into clean text suitable for claim extraction.
- Track ingestion status end-to-end with audit-friendly metadata.

## Storage Layout

- `Settings.ingest_bucket_path` (default `data/uploads/`): original files keyed by UUID + original filename.
- `Settings.processed_text_path` (default `data/processed/`): normalized UTF-8 text per document (`{document_id}.txt`).
- Metadata in `Document.raw_path` / `Document.text_path` keeps pointers to these assets; long-term plan is to swap to S3-compatible storage with the same interface.

## Pipeline Stages

1. **Upload API (`POST /v1/documents`)**
   - `multipart/form-data` fields:
     - `file` (required): PDF, image, or `.txt`.
     - `title` (optional)
     - `source_type` (optional, defaults to `upload`)
   - Response: `DocumentRead` schema containing IDs, storage paths, ingest status.
   - Stores the raw artifact via `IngestionService.store_raw`, creates DB record, returns status, and enqueues a background job.
2. **OCR / Text Extraction Job**
   - Executed via `run_ingestion_job` (FastAPI `BackgroundTasks` for now, upgradeable to Celery/Arq).
   - Backend selection order (`CompositeOCRBackend`):
     1. `PlainTextOCRBackend` for `.txt`/`.md`
     2. `DocxOCRBackend` using `python-docx`
     3. `PdfTextOCRBackend` using `pdfplumber`
   - Future extensions (not yet wired): raster OCR via pytesseract/rapidocr, cloud OCR (Vision/Azure) for scanned images.
   - Future: optional cloud OCR (Google Vision/Azure) adapter implementing `OCRBackend`.
3. **Normalization**
   - Clean whitespace, remove headers/footers, split paragraphs.
   - Write output via `IngestionService.persist_text`, update `Document.text_path`.
4. **Status Update**
   - On success: `ingest_status="succeeded"`, timestamp `updated_at`, path stored.
   - On failure: `ingest_status="failed"`, capture `ingest_failure_reason`, allow retries or manual review.
5. **Downstream Hooks**
   - Publish event/queue message triggering claim extraction and embedding pipeline.
   - `/v1/documents/{id}` returns latest status + storage metadata; `/v1/documents` lists recent uploads.

## Async Execution

- Job queue abstraction (`backend/app/worker/queue.py`) supports:
  - `SyncJobQueue` (default dev/test) processes inline.
  - `ArqJobQueue` pushes jobs to Redis via `arq`; run workers with `arq backend.app.worker.jobs.WorkerSettings`.
- Configure via env:
  - `QUEUE_BACKEND=arq` and `REDIS_DSN=redis://localhost:6379/0` to enable Redis-backed processing.
  - fallback/default: `QUEUE_BACKEND=sync`.
- Tasks are idempotent and keyed by document ID; failed jobs update `ingest_failure_reason`.
- For retries, rely on worker strategy (arq retry hooks) or re-enqueue from API/admin tools.

## Security & Validation

- Enforce file size/type limits (configurable).
- Virus scan hook (future) before storage if handling untrusted files.
- Log ingestion actions with document IDs for traceability.
