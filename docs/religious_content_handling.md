# Religious Content Handling

## Problem
The fact-checking system was incorrectly scoring religious texts (like the Bible, Torah) as if they were factual claims. Religious texts are not meant to be fact-checked - they are sacred texts, not historical claims.

## Solution
Added content classification to detect and handle religious/mythological content appropriately.

## How It Works

### 1. Content Classification
- **Detects**: Religious texts, mythological content, historical fiction
- **Methods**: 
  - Heuristic-based (fast, no API calls)
  - LLM-based (more accurate, uses Gemini API)

### 2. Classification Indicators

**Religious Text Indicators:**
- Biblical references (Genesis, Exodus, etc.)
- Religious terminology (God, Lord, Scripture, etc.)
- Verse/chapter structure
- Religious figures (Moses, Abraham, etc.)

**Mythological Indicators:**
- "Once upon a time"
- "Legend", "myth", "fable"
- Creation stories
- Origin stories

### 3. Handling Religious Content

When religious/mythological content is detected:
- **Verdict**: `not_applicable` (instead of supported/contradicted/no_evidence)
- **Score**: `null` (no score assigned)
- **Rationale**: Explains why it's not applicable
- **Excluded from scoring**: Not included in overall document score calculation

## Verdict Types

1. **supported**: Evidence clearly supports the claim
2. **partial**: Evidence partially supports the claim
3. **contradicted**: Evidence contradicts the claim
4. **no_evidence**: No relevant evidence found
5. **not_applicable**: Content is not factual (religious/mythological) ✨ NEW

## Example

**Input**: "In the beginning God created the heaven and the earth."

**Classification**:
- Content Type: `religious`
- Confidence: `0.90`
- Is Religious: `true`

**Result**:
- Verdict: `not_applicable`
- Score: `null`
- Rationale: "This appears to be religious content, not a factual claim to verify. Detected religious text indicators (e.g., biblical references, religious terminology)"

## Impact on Scoring

- **Before**: Religious texts got low scores (e.g., 46/100) because claims couldn't be verified
- **After**: Religious texts are marked as `not_applicable` and excluded from scoring
- **Overall Score**: Only calculated from factual claims (excludes `not_applicable`)

## Configuration

The classifier uses heuristics by default. For better accuracy, set `GEMINI_API_KEY` in `.env` to use LLM-based classification.

## Frontend Display

- Shows "Not Applicable" count in verdict breakdown
- Displays claims with gray badge for `not_applicable`
- Explains why content is not applicable in rationale

## Use Cases

This is especially important for:
- **Bible/Torah/Quran**: Sacred texts, not historical claims
- **Mythological stories**: Legends and fables
- **Religious narratives**: Stories of faith, not fact-checkable events
- **Poetic/allegorical content**: Symbolic meaning, not literal truth

## Technical Details

### Classification Service
- Location: `backend/app/services/content_classifier.py`
- Supports both heuristic and LLM-based classification
- Automatically falls back to heuristics if LLM unavailable

### Integration Points
- **Claim Extraction**: Can classify during extraction (future enhancement)
- **Verification**: Classifies before verification to skip unnecessary processing
- **Results**: Excludes `not_applicable` from score calculation

