# Claim Extraction Plan

## Goals
- Read normalized text produced by ingestion.
- Split content into discrete factual claims suitable for verification.
- Persist claims with spans, metadata, and evaluation hooks to the database.

## Pipeline Contract
1. **Inputs**
   - `document_id`: reference to a `Document` row with `text_path`.
   - Normalized text blob (UTF-8) retrieved from storage.
   - Optional contextual metadata (source type, title) to guide prompts.
2. **Extraction**
   - Initial extractor: LLM prompt (OpenAI GPT) returning structured JSON.
   - Alternate fallback: heuristic sentence splitter for tests/offline mode.
3. **Outputs**
   - `Claim` rows containing:
     - `text`: claim text.
     - `span_start` / `span_end`: character offsets in the normalized text.
     - `verdict` / `score`: left `NULL` initially, populated downstream.
     - `rationale`: optional extraction notes (e.g., prompt reasoning).
     - `metadata` JSON: prompt version, model, confidence.
4. **Evaluation Hooks**
   - Store prompt ID/version for reproducibility.
   - Capture extractor confidence to track regressions.
   - Flag low-confidence claims for manual review.
5. **Trigger**
   - Ingestion job calls extraction after OCR succeeds.
   - Re-run API endpoint to regenerate claims if document text updates.

## API Surface
- `GET /v1/documents/{id}/claims`: returns current claims (`ClaimRead` schema).
- `POST /v1/documents/{id}/claims:reextract`: runs the extractor again and returns fresh claims.
- Future work: add verdict-update endpoints once verification wiring exists.

## Extractor Backends
- Configurable via `CLAIM_EXTRACTOR`:
  - `simple` (default): regex-based sentence splitter, no external dependencies.
  - `llm`: OpenAI-backed extractor (`LLMClaimExtractor`) using `OPENAI_API_KEY` and `OPENAI_MODEL`.
- All extractor metadata (strategy, model, confidence) stored in `Claim.metadata_json`.

## Next Steps
- ✅ Implemented `ClaimExtractionService` with `HeuristicClaimExtractor`.
  - Reads normalized text, splits sentences (> configurable min length), stores `Claim` rows.
  - Deletes existing claims before re-populating to avoid duplicates.
- ✅ Ingestion worker now invokes claim extraction after OCR success.
- ☐ Expose `/v1/documents/{id}/claims` API and add regression tests for manual re-run controls.

