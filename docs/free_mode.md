# Free Mode - No API Costs!

This project supports a **completely free mode** for development and class projects that doesn't require any paid API keys.

## How to Enable Free Mode

Add this to your `.env` file:

```bash
FREE_MODE=true
```

Or simply **don't set** `OPENAI_API_KEY` - the system will automatically use free alternatives.

## What Works in Free Mode

✅ **Document Ingestion** - Fully functional
- PDF, DOCX, and text file parsing
- OCR and text extraction
- Claim extraction (using simple sentence splitter)

✅ **Evidence/RAG System** - Fully functional  
- Uses free local embeddings (`sentence-transformers`)
- No API calls needed
- Semantic search works perfectly

✅ **Claim Verification** - Mock mode
- Simulates verification based on evidence found
- Generates realistic verdicts (supported/partial/contradicted/no_evidence)
- Works great for demos and testing

## What's Different

❌ **LLM Claim Extractor** - Not available in free mode
- Use `CLAIM_EXTRACTOR=simple` (default) instead
- Simple extractor splits text into sentences (works well for most cases)

❌ **Real LLM Verification** - Uses mock verifier
- Free mode uses heuristic-based verification
- Still generates verdicts and scores, but based on evidence matching rather than LLM reasoning

## Setup Instructions

1. **Install free dependencies:**
   ```bash
   poetry install
   ```
   (sentence-transformers is already included)

2. **Set up your .env:**
   ```bash
   cp .env.example .env
   # Edit .env and set:
   FREE_MODE=true
   # Or just leave OPENAI_API_KEY empty
   ```

3. **Run the server:**
   ```bash
   poetry run uvicorn backend.app.main:app --reload
   ```

## Cost Breakdown

| Feature | Free Mode | Paid Mode (OpenAI) |
|---------|-----------|-------------------|
| Document Ingestion | ✅ Free | ✅ Free |
| Claim Extraction | ✅ Free (simple) | 💰 ~$0.01-0.10/doc |
| Evidence Embeddings | ✅ Free (local) | 💰 ~$0.0001/doc |
| Verification | ✅ Free (mock) | 💰 ~$0.01-0.05/claim |

**Total cost in free mode: $0.00** 🎉

## For Class Projects

Free mode is perfect for:
- Demonstrating the full pipeline
- Testing and development
- Learning how the system works
- Submitting assignments

The mock verification still produces realistic results that show how the system would work with real LLM verification.

