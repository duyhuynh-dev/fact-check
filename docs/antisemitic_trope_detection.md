# Antisemitic Trope Detection

## Overview
The system now detects and flags antisemitic tropes and stereotypes, even when there's no specific "fact" to verify. This is crucial because antisemitic content often uses coded language and stereotypes rather than explicit factual claims.

## New Verdict Type: `antisemitic_trope`

### What It Means
- Content uses antisemitic stereotypes or tropes
- Not a factual claim to verify, but antisemitic content to flag
- No score assigned (null) - the antisemitic nature IS the finding

### Examples Detected

**Example 1:**
> "I prefer my kids knew Hannukah from Kwanzaa. At least it will come with some financial engineering."

**Detection:**
- Pattern: `money_trope`
- Rationale: Uses coded reference to "financial engineering" in connection with Hanukkah, invoking the antisemitic stereotype that Jews are obsessed with money

**Example 2:**
> "I just think that's what they're about, is making money," West said in an apparent reference to Jared Kushner and his Jewish family.

**Detection:**
- Pattern: `money_trope`
- Rationale: Stereotypes Jewish people as primarily motivated by money

## How It Works

### 1. Semantic Analysis
- Detects antisemitic patterns during claim extraction
- Uses heuristics and/or LLM to identify coded language
- Looks for specific tropes (money, conspiracy, scapegoating, etc.)

### 2. Pattern Detection
The system detects:
- **Money tropes**: References to money/finance + Jewish people/holidays
- **Conspiracy tropes**: Secret control, networks, behind-the-scenes
- **Coded language**: Vague references ("they", "them") with negative context
- **Scapegoating**: Blame attribution patterns

### 3. Verification Logic
- If semantic analysis detects antisemitic content with confidence > 0.6
- Automatically marks as `antisemitic_trope`
- Retrieves relevant evidence about the specific trope
- Provides explanation of why it's antisemitic

### 4. Evidence Integration
- Retrieves information from `antisemitic_tropes.txt` knowledge base
- Explains the historical context of the trope
- Provides educational context about why it's harmful

## Money-Related Antisemitic Tropes

The system specifically detects:
- "Financial engineering" + Jewish reference
- "Making money" + Jewish reference  
- Money/finance + Jewish holidays (Hanukkah, etc.)
- Stereotypes about Jews being "about money"

These are flagged even without explicit "facts" to verify because:
1. They perpetuate harmful stereotypes
2. They use coded language to spread antisemitism
3. The antisemitic nature IS the finding, not something to "fact-check"

## Frontend Display

- **Verdict Badge**: Red badge labeled "Antisemitic Trope"
- **Verdict Summary**: Shows count of antisemitic trope claims
- **Rationale**: Explains which trope was detected and why it's antisemitic
- **No Score**: These claims don't get a numerical score (null)

## Technical Details

### Confidence Thresholds
- **Money tropes**: 0.75 confidence (high - these are clear antisemitic stereotypes)
- **Other tropes**: 0.3-0.9 based on number of patterns detected
- **Minimum for verdict**: 0.6 confidence required to mark as `antisemitic_trope`

### Detection Methods
1. **Heuristic**: Pattern matching for common tropes (fast, no API calls)
2. **LLM-based**: Semantic understanding of coded language (more accurate, uses Gemini API)

### Integration Points
- **Claim Extraction**: Semantic analysis runs during extraction
- **Verification**: Checks for antisemitic tropes before fact-checking
- **Results**: Excluded from scoring, but counted in verdict summary

## Why This Matters

Antisemitic content often doesn't make explicit factual claims. Instead, it uses:
- Coded language and dog whistles
- Stereotypes and tropes
- Implicit messaging

The system now recognizes that **identifying antisemitic content is itself a form of verification** - we don't need to "fact-check" a stereotype, we need to identify and explain why it's antisemitic.

## Example Workflow

1. **User uploads**: Screenshot with antisemitic trope
2. **System extracts**: Claims from the text
3. **Semantic analysis**: Detects money trope pattern
4. **Verification**: Marks as `antisemitic_trope` (no fact-checking needed)
5. **Results**: Shows red badge, explains the trope, provides educational context

## Future Enhancements

- More trope patterns (dual loyalty, blood libel, etc.)
- Context-aware detection (understanding when "they" refers to Jews)
- Educational links to ADL, IHRA definitions
- Historical context for each trope

