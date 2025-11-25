# Tone Detection Enhancement

## Problem
The system was not effectively detecting the tone and intent of antisemitic content, leading to poor classification and "No Evidence" results for clearly threatening or hostile content.

## Solution: Comprehensive Tone Analysis

### Enhanced Components

#### 1. LLM Analysis Prompt (verification_gemini.py)
**Before**: Basic prompt asking if content is antisemitic
**After**: Multi-step analysis focusing on tone, intent, and emotional weight

**New Analysis Steps**:
1. **TONE ANALYSIS**: Analyze emotional tone (threatening, hostile, aggressive, menacing, neutral, informative)
2. **INTENT ANALYSIS**: Determine what the text is trying to accomplish
3. **ANTISEMITIC INDICATORS**: Check for specific patterns
4. **CONTENT CLASSIFICATION**: Classify based on tone + intent + indicators

**New Fields in Response**:
- `tone`: "threatening" | "hostile" | "aggressive" | "menacing" | "neutral" | "informative"
- `emotional_weight`: "high" | "medium" | "low"
- `intent`: Detailed description of what the text is trying to do

#### 2. Enhanced JSON Parsing (verification_gemini.py)
**Before**: Basic JSON parsing, failed on malformed responses
**After**: Multi-method extraction with intelligent fallback

**Improvements**:
- Multiple extraction methods (```json, ```, {})
- Regex-based field extraction for tone, intent, emotional_weight
- Fallback detection: If JSON fails, extract tone/intent from response text
- Pattern matching for antisemitic keywords even in malformed JSON

#### 3. Semantic Analysis Enhancement (semantic_analysis.py)
**Before**: Basic pattern matching
**After**: Tone-aware analysis with intent detection

**New Features**:
- Tone detection in LLM semantic analyzer
- Tone inference in heuristic analyzer
- Intent analysis (what the text is trying to do)
- Emotional weight assessment

**Updated SemanticAnalysis Dataclass**:
```python
@dataclass
class SemanticAnalysis:
    # ... existing fields ...
    tone: str | None = None  # e.g., "threatening", "hostile", "neutral"
    emotional_weight: str | None = None  # e.g., "high", "medium", "low"
    intent: str | None = None  # Description of what the text is trying to do
```

#### 4. Heuristic Tone Detection (semantic_analysis.py)
**New Logic**:
- Detects tone based on patterns:
  - `threatening_language` → tone: "threatening", emotional_weight: "high"
  - `conspiracy_trope` + Jewish reference → tone: "hostile", emotional_weight: "medium"
  - Coded language → tone: "hostile", emotional_weight: "medium"
- Generates intent descriptions based on detected patterns

#### 5. Pre-Verification Enhancement (tasks.py)
**Before**: Basic semantic analysis check
**After**: Includes tone, emotional_weight, and intent in rationale

**New Rationale Format**:
```
This content is antisemitic. [explanation]. Tone: [tone]. Emotional weight: [weight]. Intent: [intent]. Detected patterns: [patterns].
```

## Example Analysis

### Input Text:
> "This ain't a game. Imma use you as an example to show the Jewish people that told you to call me that no one can threaten or influence me. I told you this is war. Now gone get you some business."

### Analysis Result:
```json
{
  "is_antisemitic": true,
  "content_type": "antisemitic_trope",
  "tone": "threatening",
  "emotional_weight": "high",
  "intent": "To intimidate and threaten Jewish people, declaring war and suggesting harm",
  "detected_patterns": ["threatening_language", "secret_control"],
  "confidence": 0.90,
  "explanation": "Contains threatening language directed at Jewish people. Tone is threatening with high emotional weight. Intent is to intimidate and threaten."
}
```

### Rationale:
> "This content is antisemitic. Contains threatening language directed at Jewish people. Tone: threatening. Emotional weight: high. Intent: To intimidate and threaten Jewish people. Detected patterns: threatening_language, secret_control."

## Benefits

1. **Better Detection**: Tone analysis helps identify antisemitic content even when keywords are subtle
2. **Richer Context**: Intent and emotional weight provide deeper understanding
3. **Robust Parsing**: Multiple fallback methods ensure tone/intent are extracted even from malformed responses
4. **Comprehensive Rationale**: Users see not just what patterns were detected, but the tone and intent behind the content
5. **Multi-Layer Defense**: Tone analysis happens at multiple levels (pre-verification, LLM analysis, semantic analysis)

## Testing

Test with threatening tweets - they should now show:
- Verdict: `antisemitic_trope`
- Tone: `threatening` or `hostile`
- Emotional weight: `high`
- Intent: Clear description of threatening intent
- Rationale: Comprehensive explanation including tone and intent

