# fact-check

Prototype roadmap for an antisemitism-oriented fact-checking assistant.

## Vision

- ingest antisemitism-related content (PDFs, images, plain text) and normalize it
- extract factual claims and inflammatory rhetoric cues
- retrieve evidence from a vetted antisemitism knowledge base (libraries, museums, watchdog orgs)
- verify each claim, highlight misleading sections, and compute an overall risk/accuracy score
- output a transparent report with citations and uncertainty notes

## High-Level Architecture

1. **Ingestion & OCR**
   - upload endpoint, PDF parsing, image OCR (Tesseract or cloud OCR)
   - text normalization, sentence segmentation, metadata capture
2. **Claim & Cue Extraction**
   - LLM or rule-based splitter to isolate factual statements
   - detector for conspiracy tropes, slurs, and framing language
3. **Evidence Retrieval (RAG)**
   - curated corpora (Holocaust Encyclopedia, ADL reports, academic journals)
   - embedding store + hybrid keyword search for grounding passages
4. **Claim Verification & Scoring**
   - per-claim verdicts: Supported, Partial, Contradicted, No Evidence
   - score aggregation (0–100) with deductions for rhetoric cues
   - rationale text + citations stored for audit
5. **Reporting & Docs**
   - UI/API summary with highlighted text, evidence snippets, downloadable report
   - documentation explaining data sources, limitations, safety review

## Work Plan

1. **Documentation & Repo Setup**
   - ✅ Stack chosen: Python 3.11, FastAPI, LangChain/LlamaIndex, PostgreSQL + pgvector.
   - ✅ Repo skeleton + starter docs (`docs/architecture.md`, `docs/contributing.md`).
2. **Data & Knowledge Base**
   - Identify public antisemitism corpora, licensing constraints.
   - Build ingestion scripts and metadata schema.
3. **Claim Extraction Prototype**
   - Evaluate LLM prompts vs lightweight classifiers.
   - Collect evaluation set for tuning.
4. **Retriever + Evidence Store**
   - Stand up vector DB (e.g., Chroma, pgvector).
   - Implement hybrid search API with caching.
5. **Verifier & Scoring**
   - Prompt templates, weighting scheme, calibration.
   - Confidence estimation + uncertainty flags.
6. **UI/API Layer**
   - Minimal web dashboard showing verdicts and score.
   - Export pipeline (PDF/JSON report).
7. **Evaluation & Safety Review**
   - Red-team scenarios, bias analysis, human-in-the-loop workflow.

## Current Milestone — Step 2 Scope

- **Persistence layer**
  - Stand up SQLModel metadata plus base `Document`, `Claim`, and `Evidence` tables with pgvector-friendly embeddings.
  - Configure Postgres connection settings, health checks, and migration tooling (Alembic runner).
  - Define storage directories/S3 layouts for raw artifacts vs processed text; map records to files via metadata.
- **Ingestion + OCR prep**
  - Establish upload contract for `/v1/documents` (multipart file + metadata), response schema, and status polling endpoint.
  - Specify OCR flow: pdfplumber for text PDFs, fallback to raster extraction via pytesseract, optional rapidocr for complex scripts.
  - Plan async job hooks (Arq/Celery placeholder) to offload OCR + claim extraction; capture failure + retry strategy.
- **Outputs for this step**
  - Schema scaffolding, connection utilities, ingestion module stubs, and documentation describing how documents move from upload → OCR → normalized text.

## Documentation Plan

- `README`: vision, architecture, quick start.
- `docs/architecture.md`: diagrams, data flow, RAG pipeline details.
- `docs/datasets.md`: sources, licensing, update cadence.
- `docs/safety.md`: limitations, review procedures, escalation paths.
- `docs/api.md`: endpoints for ingestion, verification, reporting.
- Maintain changelog and decision log (ADR format) for major design choices.
