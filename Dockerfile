FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Poetry
RUN pip install poetry==1.8.3

# Copy dependency files
COPY pyproject.toml ./

# Configure Poetry
RUN poetry config virtualenvs.create false

# Install dependencies - let Poetry resolve dependencies
# This will work even if poetry.lock is out of sync
RUN poetry install --no-dev --no-interaction --no-ansi || \
    (echo "First attempt failed, trying without lock file..." && \
     poetry lock --no-update && \
     poetry install --no-dev --no-interaction --no-ansi)

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/uploads data/processed vectorstore

# Expose port
EXPOSE 8000

# Run the application
# Use PORT environment variable if set (for Render), otherwise default to 8000
CMD sh -c "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"

