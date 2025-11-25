# Backend Improvements Summary

## 1. Enhanced Evidence Matching (Hybrid Search)

### What Changed
- **Hybrid Search**: Combines semantic (embedding) similarity + keyword matching
- **Configurable Thresholds**: `EVIDENCE_MIN_SIMILARITY` (default: 0.3) filters low-quality matches
- **Keyword Boosting**: Important terms get up to 0.2 similarity boost
- **Better Ranking**: Results sorted by combined score (semantic + keyword)

### Benefits
- More relevant evidence retrieval
- Better handling of specific terms (e.g., "Zionist", "Holocaust")
- Reduces false positives from semantic-only search
- Configurable sensitivity via environment variables

### Configuration
```bash
EVIDENCE_MIN_SIMILARITY=0.3  # Lower = more results, Higher = stricter matching
EVIDENCE_RETRIEVAL_LIMIT=5   # Number of evidence snippets per claim
```

## 2. Improved Claim Extraction

### What Changed
- **Conspiracy Theory Detection**: Identifies conspiracy language patterns
- **Antisemitic Keyword Detection**: Flags claims with antisemitic terminology
- **Importance Scoring**: Ranks claims by relevance (antisemitic content gets higher priority)
- **Better Entity Recognition**: Detects more entity types (EVENT, etc.)
- **Responsibility Verb Detection**: Catches blame/responsibility claims

### Benefits
- Better extraction of problematic claims
- Prioritizes antisemitic content for verification
- More nuanced claim identification
- Catches conspiracy theory patterns

### Metadata Added
- `has_conspiracy_language`: Boolean flag
- `has_antisemitic_keywords`: Boolean flag  
- `importance_score`: Numerical score (higher = more important to verify)

## 3. Expanded Knowledge Base

### New Evidence Documents
1. **zionism_facts.txt** - Historical facts about Zionism vs. conspiracy theories
2. **antisemitic_tropes.txt** - Common antisemitic tropes and how to identify them
3. **conspiracy_theories_debunked.txt** - Debunking of common conspiracy theories
4. **israel_palestine_history.txt** - Historical context about Israel/Palestine
5. **holocaust_facts.txt** - Comprehensive Holocaust facts

### Improved Chunking
- **Smart Paragraph Splitting**: Handles long paragraphs better
- **Overlapping Windows**: Creates overlapping sentence windows for better context
- **Metadata Tracking**: Tracks chunk type and index for debugging

### Benefits
- More comprehensive coverage of antisemitic topics
- Better evidence matching for specific claims
- More nuanced fact-checking
- Reduced "no_evidence" verdicts

## 4. Configuration Improvements

### New Settings
- `EVIDENCE_MIN_SIMILARITY`: Minimum similarity threshold (0.0-1.0)
- `EVIDENCE_RETRIEVAL_LIMIT`: Max evidence snippets per claim

### Usage
All improvements are automatically active. You can tune performance via `.env`:
```bash
EVIDENCE_MIN_SIMILARITY=0.25  # More lenient (more results)
EVIDENCE_MIN_SIMILARITY=0.4   # Stricter (fewer, higher quality results)
```

## Testing the Improvements

1. **Re-upload your test document** - New claim extraction will catch more nuanced claims
2. **Check evidence matching** - Should see more relevant evidence snippets
3. **Review verdicts** - Should see fewer "no_evidence" and more "contradicted" verdicts

## Next Steps

- Fine-tune similarity thresholds based on your test results
- Add more evidence documents as needed
- Monitor claim importance scores to see what's being prioritized

