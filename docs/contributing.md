# Contributing Guide

## Prerequisites

- Python 3.11
- Poetry >= 1.8
- Tesseract OCR installed locally (`brew install tesseract` on macOS)
- Access to configured LLM/embedding providers (OpenAI key for now)

## Setup

```bash
poetry install
poetry shell
cp .env.example .env  # populate secrets
```

## Dev Workflow

1. `ruff` + `black` for lint/format.
2. `pytest` (with `pytest-asyncio`) for unit/integration tests.
3. Use feature branches + PRs; keep commits scoped.
4. Update docs (`README`, `docs/architecture.md`, `docs/safety.md`) when behavior changes.

## Commit Hygiene

- Reference issue IDs where applicable.
- Include reasoning in body for riskier changes (model updates, data migrations).
- Run `pre-commit run --all-files` before pushing.
