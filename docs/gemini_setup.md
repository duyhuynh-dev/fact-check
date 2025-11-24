# Gemini API Setup (Free Tier)

Google Gemini offers a **generous free tier** perfect for class projects!

## Get Your Free API Key

1. **Go to Google AI Studio:**
   - Visit: https://aistudio.google.com/
   - Sign in with your Google account

2. **Get API Key:**
   - Click "Get API Key" in the left sidebar
   - Create a new API key (or use existing)
   - Copy the key (starts with `AIza...`)

3. **Add to `.env`:**
   ```bash
   GEMINI_API_KEY=AIza...your-key-here
   VERIFICATION_PROVIDER=gemini
   CLAIM_EXTRACTOR=spacy
   ```

## Free Tier Limits

- **60 requests per minute** (very generous!)
- **1,500 requests per day**
- **32,000 tokens per minute**
- **1 million tokens per day**

This is more than enough for class projects and demos!

## Setup spaCy (for claim extraction)

1. **Install spaCy model:**
   ```bash
   poetry run python -m spacy download en_core_web_sm
   ```

2. **Set in `.env`:**
   ```bash
   CLAIM_EXTRACTOR=spacy
   ```

## Cost Comparison

| Provider | Free Tier | Cost After Free Tier |
|----------|-----------|---------------------|
| **Gemini** | ✅ 60 req/min, 1.5K/day | Very affordable |
| OpenAI | ❌ No free tier | ~$0.01-0.10/request |
| Free Mode | ✅ Unlimited | $0.00 (mock only) |

## Recommended Setup for Class Projects

```bash
# .env
GEMINI_API_KEY=your_key_here
VERIFICATION_PROVIDER=gemini
CLAIM_EXTRACTOR=spacy
```

This gives you:
- ✅ Real AI-powered verification (not mock)
- ✅ Smart claim extraction with NLP
- ✅ $0.00 cost (within free tier limits)
- ✅ Professional results

Perfect for demonstrating your project! 🎉

