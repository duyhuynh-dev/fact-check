FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install dependencies directly with pip (more reliable than Poetry in Docker)
COPY requirements.txt ./

# Upgrade pip first for better dependency resolution
RUN pip install --upgrade pip setuptools wheel

# Install dependencies from requirements.txt
# Use --no-deps for packages with extras, then install them separately
RUN pip install --no-cache-dir -r requirements.txt || \
    (echo "First attempt failed, trying with relaxed constraints..." && \
     pip install --no-cache-dir \
        fastapi uvicorn[standard] python-multipart \
        "pydantic>=2.7.4" "pydantic-settings>=2.1.0" \
        sqlmodel "psycopg[binary]" httpx \
        llama-index langchain langchain-openai \
        openai numpy scikit-learn pillow pytesseract \
        pdfplumber rapidocr-onnxruntime pdf2image \
        tenacity python-docx arq spacy \
        google-generativeai sentence-transformers pypdf)

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy backend code first
COPY backend/ ./backend/
COPY pyproject.toml requirements.txt ./

# Copy frontend directory (must exist in build context)
COPY frontend/ ./frontend/

# Copy evidence data (must exist in build context)
COPY data/evidence/ ./data/evidence/

# Verify frontend was copied
RUN echo "=== Verifying frontend directory ===" && \
    ls -la /app/ && \
    if [ -d "/app/frontend" ]; then \
        echo "✓ Frontend directory found"; \
        echo "Frontend contents:"; \
        ls -la /app/frontend/; \
    else \
        echo "✗ ERROR: Frontend directory NOT found"; \
        echo "Root directory contents:"; \
        ls -la /app/; \
        exit 1; \
    fi

# Create necessary directories
RUN mkdir -p data/uploads data/processed vectorstore

# Expose port
EXPOSE 8000

# Run the application
# Use PORT environment variable if set (for Render), otherwise default to 8000
CMD sh -c "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"

