# Backend Logic Improvements

## 1. Enhanced PDF Support (Scanned Books)

### What Changed
- **OCR Fallback**: PDFs now automatically use OCR if pdfplumber finds no text
- **RapidOCR Integration**: Uses `rapidocr-onnxruntime` for scanned document processing
- **Image Conversion**: Converts PDF pages to images for OCR processing

### Requirements
For scanned PDF support, you need:
- **macOS**: `brew install poppler`
- **Linux**: `apt-get install poppler-utils` or `yum install poppler-utils`
- **Windows**: Download poppler binaries and add to PATH

### How It Works
1. First tries `pdfplumber` (fast, for selectable text PDFs)
2. If no text found → converts PDF to images
3. Runs OCR on each page using RapidOCR
4. Combines all extracted text

### Benefits
- Handles scanned books and documents
- Automatic fallback (no manual selection needed)
- Works with both text and image-based PDFs

## 2. Improved Evidence Database

### Enhanced Evidence Model
Added fields to `Evidence` model:
- `citation`: Formal citation (e.g., "ADL Report 2023, p. 45")
- `author`: Author or organization
- `publication_date`: When the source was published
- `reliability_score`: Source reliability (0-1)

### Better Metadata
- Automatic source type detection (ADL, Encyclopedia, etc.)
- Reliability scoring based on source type
- Citation tracking for auditability

### Benefits
- Better source attribution
- Reliability weighting for verification
- More professional evidence presentation
- Easier to trace back to original sources

## 3. Semantic/Conceptual Analysis

### What It Does
Detects antisemitic content that **doesn't use explicit keywords** by analyzing:
- **Coded language**: Terms with antisemitic meaning in context
- **Dog whistles**: Hidden messages understood by specific audiences
- **Implicit meaning**: What the text suggests without stating directly
- **Paragraph context**: Understanding flow and narrative patterns

### Implementation
- **LLM-Based Analysis**: Uses Gemini to understand semantic meaning
- **Context-Aware**: Analyzes sentences within paragraph context
- **Pattern Detection**: Identifies conspiracy tropes, scapegoating, etc.
- **Confidence Scoring**: Provides confidence levels for detections

### Detected Patterns
- `conspiracy_trope`: Secret control narratives
- `dog_whistle`: Coded antisemitic language
- `dual_loyalty`: Accusations of divided allegiance
- `scapegoating`: Blame attribution patterns
- `coded_language`: Implicit messaging
- `historical_trope`: Modern use of historical antisemitic themes

### Integration
- Runs during claim extraction
- Results stored in claim metadata
- Used by verification to understand implicit meaning
- Helps catch subtle antisemitic content

### Example
**Text**: "They control the media and influence governments behind the scenes."

**Analysis**:
- `is_antisemitic`: true
- `coded_language_detected`: true
- `implicit_meaning`: "Suggests a secret group (often coded reference to Jews) controls media and governments"
- `detected_patterns`: ["conspiracy_trope", "dog_whistle", "secret_control"]

## Configuration

Add to `.env`:
```bash
# Evidence matching
EVIDENCE_MIN_SIMILARITY=0.3
EVIDENCE_RETRIEVAL_LIMIT=5
```

## Testing

1. **Test scanned PDF**: Upload a scanned book PDF - should automatically use OCR
2. **Test semantic analysis**: Upload text with coded language (no explicit keywords)
3. **Check metadata**: Verify evidence includes citations and reliability scores

## Next Steps

- Fine-tune semantic analysis prompts
- Add more evidence sources with proper citations
- Improve reliability scoring algorithm
- Add source verification workflow

