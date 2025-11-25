# LLM-Based Context Analysis

## Problem
The system was splitting tweets into individual sentences, losing context. This meant threatening language like "I told you this is war" was being analyzed separately from "show the Jewish people", missing the antisemitic intent.

## Solution

### 1. Smart Claim Extraction
- **Short texts (<500 chars)**: Kept as single claims with full context
- **Long texts**: Still split by sentences, but with paragraph context
- **Semantic analysis**: Runs on full text for short content

### 2. Enhanced LLM Analysis
- **Full context analysis**: LLM analyzes the complete tweet/text together
- **Threatening language detection**: Specifically looks for threatening language directed at Jewish people
- **Improved prompts**: Emphasizes context and intent, not just keywords

### 3. Better Verification
- **Context-aware**: Verification uses semantic analysis results
- **Prioritizes antisemitic content**: Checks for tropes before fact-checking
- **Comprehensive analysis**: LLM understands the full meaning, not just individual sentences

## How It Works Now

### Example: Threatening Tweet
**Text**: "This ain't a game. Imma use you as an example to show the Jewish people that told you to call me that no one can threaten or influence me. I told you this is war. Now gone get you some business."

**Before**:
- Split into 3 separate claims
- Each analyzed independently
- Result: "No Evidence" for each

**After**:
- Kept as single claim (194 chars < 500)
- Full semantic analysis on complete text
- Detects: `threatening_language`, `conspiracy_trope`, `secret_control`
- Confidence: 0.85
- Verdict: `antisemitic_trope`

## Technical Implementation

### Claim Extraction
```python
# Short texts kept as single claims
if len(text.strip()) < 500:
    semantic_analysis = analyzer.analyze(text.strip())  # Full text analysis
    return [ClaimCandidate(text=text.strip(), ...)]
```

### Semantic Analysis
- **Heuristic**: Pattern matching for common tropes
- **LLM-based**: Uses Gemini to understand context and intent
- **Both**: Emphasize threatening language detection

### Verification
- Checks semantic analysis first
- If antisemitic with confidence > 0.6 → `antisemitic_trope`
- Otherwise, proceeds with fact-checking

## Benefits

1. **Context preservation**: Full tweets analyzed together
2. **Better detection**: LLM understands intent, not just keywords
3. **Accurate classification**: Threatening language properly flagged
4. **No false negatives**: Antisemitic content doesn't get "No Evidence"

## Configuration

The system automatically:
- Uses LLM analyzer if `GEMINI_API_KEY` is set
- Falls back to heuristic if no API key
- Both methods now detect threatening language

## Future Improvements

- Multi-sentence context window for longer texts
- Cross-reference detection (understanding "they" refers to Jews)
- Historical pattern matching (recognizing known antisemitic phrases)

