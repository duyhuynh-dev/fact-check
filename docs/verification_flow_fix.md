# Verification Flow Fix

## Problem
The system was showing "No Evidence" for antisemitic content because it was trying to fact-check everything, including content that should be flagged as antisemitic based on tone/intent.

## Solution: LLM-First Analysis

### New Flow (Correct)

1. **LLM Analysis FIRST** (Primary Step)
   - LLM analyzes the content to determine:
     - Is this antisemitic? (tone, intent, tropes)
     - Is this a factual claim?
     - What is the intent/purpose?
   - **LLM decides**: antisemitic → flag immediately, factual → proceed to evidence

2. **If Antisemitic** → Flag as `antisemitic_trope`
   - NO evidence lookup needed
   - Return immediately with explanation
   - No score (not a factual claim)

3. **If Factual Claim** → Retrieve evidence and compare
   - Only retrieve evidence for actual factual claims
   - Compare with knowledge base
   - Generate verdict: supported/contradicted/partial/no_evidence

4. **If Not Applicable** → Mark as `not_applicable`
   - Religious/mythological content
   - No fact-checking needed

### Old Flow (Wrong)
1. Retrieve evidence for everything
2. Try to fact-check antisemitic content
3. Show "No Evidence" when antisemitic content has no facts to verify

## Role of LLM

**LLM's Primary Role**: Analyze tone, intent, and content type FIRST
- Detects antisemitic content (threatening language, stereotypes, tropes)
- Determines if content is a factual claim
- Analyzes intent and purpose

**LLM's Secondary Role**: Fact-checking (only for factual claims)
- Only after LLM determines it's a factual claim
- Compares with evidence database
- Generates verdict based on evidence

## Implementation

### Gemini Verifier (`verification_gemini.py`)
- **Step 1**: LLM analyzes content type (antisemitic_trope vs factual_claim)
- **Step 2**: If antisemitic → flag immediately, return
- **Step 3**: If factual → retrieve evidence and fact-check
- **Step 4**: If not_applicable → mark and return

### Free Verifier (`verification_free.py`)
- Uses semantic analysis (heuristic or LLM) to detect antisemitic content first
- Flags antisemitic content before fact-checking
- Only fact-checks actual factual claims

## Result

✅ Antisemitic tweets/content → Flagged as `antisemitic_trope` with explanation
✅ Factual claims → Verified against evidence database
✅ No more "No Evidence" for antisemitic content

