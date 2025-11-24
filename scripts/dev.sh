#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v poetry >/dev/null 2>&1; then
  echo "Poetry is required. Install via https://python-poetry.org/docs/" >&2
  exit 1
fi

poetry run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

