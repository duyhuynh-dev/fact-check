"""Ingestion orchestration (upload, OCR, normalization)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from backend.app.core.config import get_settings
from backend.app.db.models import Document


class OCRBackend(Protocol):
    """Behaviour expected from OCR adapters."""

    def supports(self, input_path: Path) -> bool: ...

    def extract_text(self, input_path: Path) -> str: ...


@dataclass
class IngestionPaths:
    raw_dir: Path
    processed_dir: Path

    @classmethod
    def from_settings(cls) -> "IngestionPaths":
        settings = get_settings()
        raw = Path(settings.ingest_bucket_path)
        processed = Path(settings.processed_text_path)
        raw.mkdir(parents=True, exist_ok=True)
        processed.mkdir(parents=True, exist_ok=True)
        return cls(raw_dir=raw, processed_dir=processed)


class IngestionService:
    """Coordinates upload storage and OCR normalization."""

    def __init__(self, ocr_backend: OCRBackend):
        self.paths = IngestionPaths.from_settings()
        self.ocr_backend = ocr_backend

    def store_raw(self, file_bytes: bytes, filename: str) -> Path:
        safe_name = Path(filename).name or "upload.bin"
        unique_name = f"{uuid4()}_{safe_name}"
        target = self.paths.raw_dir / unique_name
        target.write_bytes(file_bytes)
        return target

    def run_ocr(self, source_path: Path) -> str:
        if not self.ocr_backend.supports(source_path):
            raise ValueError(f"OCR backend cannot handle {source_path.suffix or 'binary'}")
        return self.ocr_backend.extract_text(source_path)

    def persist_text(self, text: str, document: Document) -> Path:
        target = self.paths.processed_dir / f"{document.id}.txt"
        target.write_text(text)
        return target


class PlainTextOCRBackend:
    """Reads plaintext artifacts without OCR."""

    extensions = {".txt", ".md"}

    def supports(self, input_path: Path) -> bool:
        return input_path.suffix.lower() in self.extensions

    def extract_text(self, input_path: Path) -> str:
        return input_path.read_text(encoding="utf-8")


class PdfTextOCRBackend:
    """Extracts text from selectable PDFs via pdfplumber."""

    extensions = {".pdf"}

    def __init__(self) -> None:
        import pdfplumber

        self._pdfplumber = pdfplumber

    def supports(self, input_path: Path) -> bool:
        return input_path.suffix.lower() in self.extensions

    def extract_text(self, input_path: Path) -> str:
        with self._pdfplumber.open(str(input_path)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages).strip()
        if not text:
            raise ValueError("pdfplumber yielded no text; consider DOCX/plaintext formats")
        return text


class DocxOCRBackend:
    """Extracts text from DOCX files via python-docx."""

    extensions = {".docx"}

    def __init__(self) -> None:
        import docx

        self._docx = docx

    def supports(self, input_path: Path) -> bool:
        return input_path.suffix.lower() in self.extensions

    def extract_text(self, input_path: Path) -> str:
        document = self._docx.Document(str(input_path))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs).strip()
        if not text:
            raise ValueError("DOCX file contains no extractable text")
        return text


class CompositeOCRBackend:
    """Tries multiple OCR adapters in order."""

    def __init__(self, adapters: list[OCRBackend]):
        self.adapters = adapters

    def supports(self, input_path: Path) -> bool:
        return any(adapter.supports(input_path) for adapter in self.adapters)

    def extract_text(self, input_path: Path) -> str:
        for adapter in self.adapters:
            if adapter.supports(input_path):
                return adapter.extract_text(input_path)
        raise ValueError(f"No OCR backend supports {input_path.suffix or 'binary'}")


def create_default_ingestion_service() -> IngestionService:
    """Factory to build the service with default OCR backend."""
    backend = CompositeOCRBackend(
        adapters=[
            PlainTextOCRBackend(),
            DocxOCRBackend(),
            PdfTextOCRBackend(),
        ]
    )
    return IngestionService(ocr_backend=backend)

