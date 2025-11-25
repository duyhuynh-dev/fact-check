# Architecture Fix: Antisemitic Content Detection

## Problem
The system was showing "No Evidence" for clearly antisemitic content (like threatening tweets) instead of flagging it as `antisemitic_trope`.

## Root Cause
The verification flow was:
1. Extract claims
2. **Retrieve evidence** (for everything)
3. **Try to fact-check** (even antisemitic content)
4. Show "No Evidence" when antisemitic content has no facts to verify

## Solution: Multi-Layer Detection Architecture

### New Architecture (3-Layer Defense)

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Pre-Verification (Semantic Analysis)          │
│  - Runs BEFORE verifier                                  │
│  - Detects antisemitic content early                    │
│  - Flags as antisemitic_trope if detected                │
└─────────────────────────────────────────────────────────┘
                        ↓ (if not detected)
┌─────────────────────────────────────────────────────────┐
│  Layer 2: LLM Analysis (Primary Verification)             │
│  - LLM analyzes tone, intent, content type              │
│  - Flags as antisemitic_trope if detected                │
│  - Only proceeds to fact-checking if factual claim      │
└─────────────────────────────────────────────────────────┘
                        ↓ (if factual claim)
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Evidence Retrieval + Fact-Checking           │
│  - Only for actual factual claims                        │
│  - Compares with knowledge base                          │
│  - Generates verdict: supported/contradicted/etc        │
└─────────────────────────────────────────────────────────┘
```

### Implementation Details

#### Layer 1: Pre-Verification (tasks.py)
- Runs semantic analysis BEFORE calling verifier
- Uses `HeuristicSemanticAnalyzer` or `LLMSemanticAnalyzer`
- If antisemitic content detected (confidence > 0.5), flags immediately
- **Prevents antisemitic content from reaching verifier**

#### Layer 2: LLM Analysis (verification_gemini.py)
- LLM analyzes content FIRST (before evidence retrieval)
- Determines: antisemitic? factual claim? not applicable?
- If antisemitic → flag as `antisemitic_trope`, return immediately
- If factual → proceed to Layer 3
- **Improved JSON parsing with fallback** for when LLM doesn't return perfect JSON

#### Layer 3: Evidence Retrieval + Fact-Checking
- Only runs for actual factual claims
- Retrieves evidence from knowledge base
- Compares claim with evidence
- Generates verdict based on evidence

### Improvements Made

1. **Pre-Verification Step** (`tasks.py`)
   - Added semantic analysis BEFORE verifier
   - Catches antisemitic content early
   - Lower threshold (0.5) for pre-check

2. **Better JSON Parsing** (`verification_gemini.py`)
   - Multiple extraction methods
   - Fallback detection if JSON parsing fails
   - Detects antisemitic keywords in response even if JSON is malformed

3. **Improved Semantic Analyzer** (`semantic_analysis.py`)
   - Better detection of "jewish people" variations
   - More aggressive threatening language detection
   - Higher confidence scores for threatening language (0.90)
   - Better explanation generation

4. **Better Error Handling**
   - If LLM fails, falls back to semantic analysis
   - If semantic analysis fails, continues to fact-checking
   - Never silently fails to "No Evidence"

## Result

✅ Antisemitic tweets/content → Flagged as `antisemitic_trope` (red badge)
✅ Factual claims → Verified against evidence database
✅ No more "No Evidence" for antisemitic content
✅ Multiple layers of defense ensure detection even if one layer fails

## Testing

Test with the tweet:
> "This ain't a game. Imma use you as an example to show the Jewish people that told you to call me that no one can threaten or influence me. I told you this is war. Now gone get you some business."

**Expected Result**: 
- Layer 1 (Pre-Verification) should detect: `threatening_language` + `jewish people` → `antisemitic_trope`
- Verdict: `antisemitic_trope`
- Score: `None`
- Rationale: Explanation of why it's antisemitic

