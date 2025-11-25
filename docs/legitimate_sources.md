# Legitimate Sources for Learning About Judaism

## Overview
The fact-checking system recognizes that religious texts are legitimate and essential sources for learning about Judaism, even though they should not be fact-checked as historical events.

## Key Distinction

### Religious Texts as Sources
**Legitimate for:**
- Understanding Jewish beliefs and practices
- Learning about Jewish tradition and law
- Studying Jewish theology and philosophy
- Understanding Jewish community life

**Not for:**
- Fact-checking as historical events
- Verifying as literal historical accounts
- Treating as historical documents

## Legitimate Sources

### 1. Religious Texts (Sacred Sources)
- **Torah** (Five Books of Moses): Foundational text of Judaism
- **Talmud**: Central text of Rabbinic Judaism (Mishnah + Gemara)
- **Midrash**: Rabbinic interpretation of biblical texts
- **Responsa Literature**: Historical case studies and legal decisions

### 2. Foundational Legal and Philosophical Works
- **Mishneh Torah** by Maimonides: Comprehensive code of Jewish law
- **Shulchan Aruch**: Standard code of Jewish law (16th century)
- **Guide for the Perplexed** by Maimonides: Philosophical work
- **Rashi's Commentaries**: Essential Torah and Talmud commentaries

### 3. Primary Source Collections
- **Yizkor Book Collection**: Memorial books from Holocaust communities
- **Elie Wiesel Digital Archive**: Holocaust documents and testimonies
- **Central Archives for the History of the Jewish People**: Historical records
- **American Jewish Historical Society Archives**: Jewish life in America

### 4. Modern Scholarship
- **Encyclopedias**: Jewish Encyclopedia, Encyclopedia Judaica
- **Academic Journals**: Peer-reviewed Jewish studies publications
- **Scholarly Treatises**: Works by recognized scholars

## How the System Handles This

### When Religious Content is Detected:
1. **Verdict**: `not_applicable` (not fact-checked)
2. **Rationale**: Explains that religious texts are legitimate sources for learning about Judaism, but are sacred texts, not historical documents
3. **Score**: `null` (excluded from scoring)
4. **Context**: System recognizes these are valid sources for understanding Judaism

### Example Response:
```
Verdict: not_applicable
Rationale: This appears to be religious content, not a factual claim to verify. 
Detected religious text indicators. Note: Religious texts like the Torah and 
Talmud are legitimate and essential sources for learning about Judaism, Jewish 
beliefs, and Jewish practices. However, they are sacred texts, not historical 
documents to be fact-checked as events.
```

## Important Context

### What This Means:
- ✅ Religious texts ARE legitimate sources for understanding Judaism
- ✅ They should be used when learning about Jewish beliefs and practices
- ❌ They should NOT be fact-checked as historical events
- ❌ They should NOT be used to verify literal historical claims

### Example Scenarios:

**Scenario 1: Learning About Judaism**
- **Question**: "What do Jews believe about creation?"
- **Legitimate Source**: Torah, Talmud, Midrash
- **Action**: Use religious texts as sources

**Scenario 2: Historical Fact-Checking**
- **Question**: "Did the Exodus happen exactly as described?"
- **Legitimate Sources**: Archaeological evidence, historical records, scholarly analysis
- **Action**: Do NOT fact-check the Torah narrative as a historical event

**Scenario 3: Understanding Jewish Law**
- **Question**: "What are the laws of Shabbat?"
- **Legitimate Sources**: Torah, Talmud, Mishneh Torah, Shulchan Aruch
- **Action**: Use religious texts and legal codes as sources

## Antisemitic Misuse

It is important to distinguish between:
- ✅ **Legitimate study**: Using religious texts to understand Judaism
- ❌ **Antisemitic misuse**: Using religious texts to make false historical claims or promote conspiracy theories

**Example of Misuse:**
- Claiming the Torah "proves" Jews control the world → Antisemitic
- Using the Torah to understand Jewish beliefs → Legitimate scholarship

## Evidence Base

The system's evidence base now includes:
- `legitimate_jewish_sources.txt`: Information about legitimate sources for learning about Judaism
- This helps the system understand context when verifying claims about Judaism

## Technical Implementation

- **Content Classification**: Detects religious texts
- **Verification Logic**: Marks as `not_applicable` but acknowledges legitimacy
- **Rationale Generation**: Includes note about legitimate sources
- **Metadata**: Stores classification with note about source legitimacy

