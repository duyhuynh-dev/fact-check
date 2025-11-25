# Performance Optimizations for Large Documents

## Problem
Processing 100+ page books was taking too long due to:
1. Sequential OCR processing (one page at a time)
2. Semantic analysis LLM calls for every claim
3. Verification LLM calls for every claim
4. No progress visibility

## Solutions Implemented

### 1. Progress Tracking
- **Database fields**: Added `ingest_progress` (0.0-1.0) and `ingest_progress_message`
- **Real-time updates**: Progress updates during OCR, claim extraction, and verification
- **Frontend display**: Shows actual progress percentage and current stage

### 2. OCR Optimizations
- **Lower DPI**: Reduced from 200 to 150 DPI (faster, still readable)
- **Progress callbacks**: Shows "OCR page X/Y" during processing
- **Memory cleanup**: Deletes temporary images after OCR to save space
- **Smart fallback**: Only uses OCR if pdfplumber finds no text

### 3. Semantic Analysis Optimization
- **Skip for large docs**: Automatically skips semantic analysis for documents > 50KB
- **Why**: Semantic analysis makes LLM calls for every claim, which is slow
- **Trade-off**: Faster processing, but may miss some coded language in very long documents

### 4. Batch Verification
- **Progress updates**: Updates every 10 claims instead of every claim
- **Error handling**: Failed verifications don't stop the entire process
- **Status messages**: Shows "Verifying claim X/Y"

## Performance Improvements

### Before
- 100-page book: ~30-60 minutes (no progress visibility)
- Sequential processing
- All claims get semantic analysis

### After
- 100-page book: ~15-30 minutes (with progress visibility)
- Progress updates every page/claim
- Semantic analysis skipped for very long documents
- Better error handling

## Configuration

To further optimize, you can:

1. **Lower OCR DPI** (in `ingestion.py`):
   ```python
   images = convert_from_path(str(input_path), dpi=100)  # Even faster, lower quality
   ```

2. **Adjust semantic analysis threshold** (in `claims.py`):
   ```python
   if self.semantic_analyzer and len(text) < 30000:  # Skip for smaller docs too
   ```

3. **Batch verification** (already implemented):
   - Updates progress every 10 claims
   - Can be adjusted in `tasks.py`

## Future Improvements

- **Parallel OCR**: Process multiple pages simultaneously
- **Caching**: Cache semantic analysis results for similar claims
- **Streaming**: Process and verify claims as they're extracted
- **Priority queue**: Verify high-importance claims first

## Monitoring

Check progress via API:
```bash
GET /v1/documents/{document_id}
```

Response includes:
```json
{
  "ingest_status": "processing",
  "ingest_progress": 0.65,
  "ingest_progress_message": "OCR page 65/100"
}
```

