# Large Document Handling (1000+ Pages)

## Problem
Processing extremely large documents (like a 1000-page Bible) can cause:
- **Memory issues**: Loading all pages at once
- **Timeout errors**: Processing takes hours
- **Poor user experience**: No feedback during long operations

## Solutions Implemented

### 1. Page Limit Protection
- **Hard limit**: 2000 pages maximum
- **Warning threshold**: 500+ pages triggers optimized processing
- **Clear error messages**: Tells users to split files if too large

### 2. Batch Processing for OCR
- **Small docs (<500 pages)**: Process all at once (fast)
- **Large docs (500-2000 pages)**: Process in batches of 50 pages
- **Memory efficient**: Only loads one batch at a time
- **Progress tracking**: Shows "Converting pages 1-50 of 1000..."

### 3. Adaptive DPI Settings
- **Normal docs**: 150 DPI (good quality)
- **Large docs (>500 pages)**: 100 DPI (faster, still readable)
- **Trade-off**: Slightly lower quality for much faster processing

### 4. Text Extraction Optimization
- **Small docs (<100 pages)**: Extract all at once
- **Large docs (100+ pages)**: Extract page-by-page with progress
- **Shows**: "Extracting text from page 234/1000..."

### 5. Better Error Handling
- **Memory errors**: Caught and reported clearly
- **File size warnings**: Warns for files >100 MB
- **Helpful messages**: Suggests splitting files when needed

## Performance Expectations

### 1000-Page Bible (Text PDF)
- **Text extraction**: ~5-10 minutes
- **Claim extraction**: ~2-5 minutes  
- **Verification**: Depends on number of claims
- **Total**: ~15-30 minutes (with progress updates)

### 1000-Page Scanned PDF (OCR Required)
- **OCR processing**: ~2-4 hours (with batch processing)
- **Claim extraction**: ~5-10 minutes
- **Verification**: Depends on number of claims
- **Total**: ~2.5-4.5 hours (with progress updates)

⚠️ **Note**: OCR on 1000 scanned pages is extremely slow. Consider:
- Using a text-based PDF instead
- Splitting into smaller files (500 pages each)
- Processing overnight

## Recommendations

### For Best Performance:
1. **Use text-based PDFs** when possible (no OCR needed)
2. **Split large documents** into 200-500 page chunks
3. **Process during off-hours** for very large documents
4. **Monitor progress** via the API or frontend

### When to Split:
- **>1000 pages**: Consider splitting
- **>500 pages + scanned**: Definitely split
- **>2000 pages**: Must split (hard limit)

## Configuration

To adjust limits, modify `backend/app/services/ingestion.py`:
```python
# Change page limit
if total_pages > 2000:  # Adjust this number

# Change batch size
batch_size = 50 if is_very_large else 200  # Adjust batch sizes

# Change DPI
dpi = 100 if is_very_large else 150  # Adjust DPI
```

## Future Improvements

- **Parallel processing**: Process multiple pages simultaneously
- **Resume capability**: Resume from last processed page if interrupted
- **Streaming**: Process and save text incrementally
- **Cloud processing**: Offload to cloud workers for huge documents

