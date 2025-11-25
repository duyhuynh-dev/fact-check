# System Flow Explanation

## How It Should Work

### User's Vision:
1. **Upload/Paste Input** → User provides text (tweet, document, etc.)
2. **Analyze** → System analyzes the content for:
   - Antisemitic tone/intent
   - Factual claims
   - Problematic language
3. **Compare with Sources** → If it's a factual claim, compare with evidence database
4. **Tone Analysis** → If obscure/antisemitic, analyze tone to determine intent
5. **Generate Results** → Output verdict based on analysis

## Current Problem

The system is:
- ❌ Trying to fact-check antisemitic content (wrong approach)
- ❌ Showing "No Evidence" for antisemitic tweets (should flag as antisemitic)
- ❌ Not using LLM to analyze tone/intent first
- ❌ Treating everything as a factual claim to verify

## What Should Happen

### Step 1: LLM Analysis (FIRST)
**Role of LLM**: Analyze the content to determine:
- Is this antisemitic? (tone, intent, tropes)
- Is this a factual claim?
- What is the intent/purpose?

**LLM should decide**:
- If antisemitic → Flag as `antisemitic_trope` (DONE, no fact-checking needed)
- If factual claim → Proceed to evidence comparison
- If unclear → Analyze tone/intent more deeply

### Step 2: Evidence Comparison (ONLY for factual claims)
- Only if LLM determines it's a factual claim
- Compare with evidence database
- Generate verdict: supported/contradicted/partial/no_evidence

### Step 3: Results
- Antisemitic content → `antisemitic_trope` (red badge, explanation)
- Factual claims → Verdict based on evidence
- Religious content → `not_applicable`

## The Fix

The LLM should analyze FIRST, before evidence retrieval:
1. **LLM analyzes**: "Is this antisemitic? What's the tone/intent?"
2. **If antisemitic**: Flag immediately, no evidence lookup needed
3. **If factual**: Then retrieve evidence and compare
4. **If unclear**: Use LLM to analyze tone more deeply

