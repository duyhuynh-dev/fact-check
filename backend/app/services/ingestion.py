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

    def extract_text(self, input_path: Path, progress_callback=None) -> str: ...


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

    def run_ocr(self, source_path: Path, progress_callback=None) -> str:
        if not self.ocr_backend.supports(source_path):
            raise ValueError(f"OCR backend cannot handle {source_path.suffix or 'binary'}")
        # Pass progress callback if OCR backend supports it
        if hasattr(self.ocr_backend, 'extract_text_with_progress'):
            return self.ocr_backend.extract_text_with_progress(source_path, progress_callback)
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

    def extract_text(self, input_path: Path, progress_callback=None) -> str:
        return input_path.read_text(encoding="utf-8")


class PdfTextOCRBackend:
    """Extracts text from selectable PDFs via pdfplumber, falls back to OCR for scanned pages."""

    extensions = {".pdf"}

    def __init__(self) -> None:
        import pdfplumber

        self._pdfplumber = pdfplumber

    def supports(self, input_path: Path) -> bool:
        return input_path.suffix.lower() in self.extensions

    def extract_text(self, input_path: Path, progress_callback=None) -> str:
        """Try pdfplumber first, fall back to OCR for scanned pages."""
        try:
            with self._pdfplumber.open(str(input_path)) as pdf:
                total_pages = len(pdf.pages)
                
                # Hard limit for extremely large documents
                if total_pages > 2000:
                    raise ValueError(
                        f"Document too large ({total_pages} pages). Maximum supported: 2000 pages. "
                        "Please split into smaller files."
                    )
                
                # For very large documents, warn user
                if total_pages > 500 and progress_callback:
                    progress_callback(0.0, f"Large document detected ({total_pages} pages). This may take a while...")
                
                # Extract text page by page for large docs to show progress
                if total_pages > 100:
                    pages_text = []
                    for i, page in enumerate(pdf.pages):
                        if progress_callback:
                            progress_callback(i / total_pages, f"Extracting text from page {i+1}/{total_pages}")
                        page_text = page.extract_text() or ""
                        pages_text.append(page_text)
                    text = "\n".join(pages_text).strip()
                else:
                    # For smaller docs, extract all at once (faster)
                    pages = [page.extract_text() or "" for page in pdf.pages]
                    text = "\n".join(pages).strip()
            
            # If pdfplumber got no text, it's likely a scanned PDF - use OCR
            if not text or len(text) < 50:
                return self._extract_with_ocr(input_path, progress_callback)
            
            return text
        except ValueError:
            # Re-raise ValueError (like page limit)
            raise
        except Exception:
            # If pdfplumber fails, try OCR
            return self._extract_with_ocr(input_path, progress_callback)

    def _extract_with_ocr(self, input_path: Path, progress_callback=None) -> str:
        """Extract text from scanned PDF using OCR with progress tracking and batch processing for large docs."""
        try:
            from rapidocr_onnxruntime import RapidOCR
            from pdf2image import convert_from_path
            import tempfile
            import os

            # First, check PDF page count to determine processing strategy
            try:
                with self._pdfplumber.open(str(input_path)) as pdf:
                    total_pages = len(pdf.pages)
            except Exception:
                total_pages = None  # Unknown, will process normally

            # Hard limit for OCR on extremely large documents
            if total_pages and total_pages > 2000:
                raise ValueError(
                    f"Document too large for OCR ({total_pages} pages). Maximum supported: 2000 pages. "
                    "Please split into smaller files or use a text-based PDF."
                )
            
            # For very large documents (>500 pages), use aggressive optimizations
            is_very_large = total_pages and total_pages > 500
            dpi = 100 if is_very_large else 150  # Lower DPI for huge docs
            batch_size = 50 if is_very_large else 200  # Process in smaller batches
            
            if is_very_large and progress_callback:
                progress_callback(0.0, f"Large document detected ({total_pages} pages). Using optimized processing...")

            ocr = RapidOCR()
            pages_text = []

            # Convert PDF pages to images in batches to save memory
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    # For very large docs, process page ranges
                    if is_very_large and total_pages:
                        # Process in batches to avoid memory issues
                        for batch_start in range(0, total_pages, batch_size):
                            batch_end = min(batch_start + batch_size, total_pages)
                            if progress_callback:
                                progress_callback(
                                    batch_start / total_pages,
                                    f"Converting pages {batch_start+1}-{batch_end} of {total_pages}..."
                                )
                            
                            # Convert batch of pages
                            images = convert_from_path(
                                str(input_path),
                                dpi=dpi,
                                first_page=batch_start + 1,
                                last_page=batch_end
                            )
                            
                            # Process this batch
                            for i, image in enumerate(images):
                                page_num = batch_start + i
                                if progress_callback:
                                    progress_callback(
                                        page_num / total_pages,
                                        f"OCR page {page_num+1}/{total_pages}"
                                    )
                                
                                img_path = os.path.join(temp_dir, f"page_{page_num}.png")
                                image.save(img_path, "PNG")
                                
                                result, _ = ocr(img_path)
                                if result:
                                    page_text = "\n".join([line[1] for line in result if line[1]])
                                    pages_text.append(page_text)
                                
                                # Clean up immediately
                                try:
                                    os.remove(img_path)
                                except Exception:
                                    pass
                    else:
                        # Normal processing for smaller docs
                        images = convert_from_path(str(input_path), dpi=dpi)
                        total_pages = len(images)
                        
                        for i, image in enumerate(images):
                            if progress_callback:
                                progress_callback(i / total_pages, f"OCR page {i+1}/{total_pages}")
                            
                            img_path = os.path.join(temp_dir, f"page_{i}.png")
                            image.save(img_path, "PNG")
                            
                            result, _ = ocr(img_path)
                            if result:
                                page_text = "\n".join([line[1] for line in result if line[1]])
                                pages_text.append(page_text)
                            
                            try:
                                os.remove(img_path)
                            except Exception:
                                pass
                except Exception as e:
                    if "poppler" in str(e).lower() or "convert" in str(e).lower():
                        raise ValueError("Could not convert PDF to images. Install poppler: brew install poppler (macOS) or apt-get install poppler-utils (Linux)")
                    raise

            text = "\n\n".join(pages_text).strip()
            if not text:
                raise ValueError("OCR yielded no text from PDF")
            return text
        except ImportError:
            raise ValueError(
                "OCR dependencies not installed. For scanned PDFs, install: "
                "poetry add pdf2image pillow && brew install poppler (macOS)"
            )
        except Exception as e:
            raise ValueError(f"OCR extraction failed: {str(e)}")


class ImageOCRBackend:
    """Extracts text from images (screenshots, photos) using OCR."""

    extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif"}

    def __init__(self) -> None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            self.ocr = RapidOCR()
        except ImportError:
            raise ImportError(
                "rapidocr-onnxruntime not installed. Install with: poetry add rapidocr-onnxruntime"
            )

    def supports(self, input_path: Path) -> bool:
        return input_path.suffix.lower() in self.extensions

    def extract_text(self, input_path: Path, progress_callback=None) -> str:
        """Extract text from image using OCR."""
        if progress_callback:
            progress_callback(0.0, "Processing image with OCR...")
        
        try:
            # Run OCR on the image
            result, _ = self.ocr(str(input_path))
            
            if progress_callback:
                progress_callback(0.5, "Extracting text from image...")
            
            if not result:
                raise ValueError("OCR found no text in the image")
            
            # Combine all detected text lines
            text = "\n".join([line[1] for line in result if line[1]]).strip()
            
            if progress_callback:
                progress_callback(1.0, "Text extraction complete")
            
            if not text:
                raise ValueError("No text could be extracted from the image")
            
            return text
        except Exception as e:
            if "no text" in str(e).lower() or "not found" in str(e).lower():
                raise ValueError(f"Could not extract text from image: {str(e)}")
            raise ValueError(f"OCR processing failed: {str(e)}")


class DocxOCRBackend:
    """Extracts text from DOCX files via python-docx."""

    extensions = {".docx"}

    def __init__(self) -> None:
        import docx

        self._docx = docx

    def supports(self, input_path: Path) -> bool:
        return input_path.suffix.lower() in self.extensions

    def extract_text(self, input_path: Path, progress_callback=None) -> str:
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
            ImageOCRBackend(),  # Add image support for screenshots
        ]
    )
    return IngestionService(ocr_backend=backend)

