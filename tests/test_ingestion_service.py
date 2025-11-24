from pathlib import Path

import pytest

from backend.app.services.ingestion import (
    CompositeOCRBackend,
    DocxOCRBackend,
    IngestionService,
    PlainTextOCRBackend,
    PdfTextOCRBackend,
)

FIXTURES_DIR = Path(__file__).parent


def test_plain_text_backend_reads_file(tmp_path: Path) -> None:
    sample = tmp_path / "note.txt"
    sample.write_text("hello world", encoding="utf-8")

    backend = PlainTextOCRBackend()
    assert backend.supports(sample)
    assert backend.extract_text(sample) == "hello world"


class StubBackend:
    def __init__(self, suffix: str, response: str):
        self.suffix = suffix
        self.response = response
        self.called = False

    def supports(self, input_path: Path) -> bool:
        return input_path.suffix == self.suffix

    def extract_text(self, input_path: Path) -> str:
        self.called = True
        return self.response


def test_composite_backend_selects_correct_adapter(tmp_path: Path) -> None:
    sample = tmp_path / "doc.foo"
    sample.write_bytes(b"binary")

    first = StubBackend(".bar", "bar text")
    second = StubBackend(".foo", "foo text")

    composite = CompositeOCRBackend(adapters=[first, second])
    assert composite.supports(sample)
    assert composite.extract_text(sample) == "foo text"
    assert second.called
    assert not first.called


def test_ingestion_service_raises_for_unsupported(tmp_path: Path) -> None:
    sample = tmp_path / "doc.bin"
    sample.write_bytes(b"binary data")

    backend = PlainTextOCRBackend()
    service = IngestionService(ocr_backend=backend)

    with pytest.raises(ValueError):
        service.run_ocr(sample)


def test_pdf_backend_reads_fixture() -> None:
    backend = PdfTextOCRBackend()
    pdf_path = FIXTURES_DIR / "hello.pdf"
    assert backend.supports(pdf_path)
    assert backend.extract_text(pdf_path).strip() == "Hello PDF"


def test_docx_backend_reads_fixture() -> None:
    backend = DocxOCRBackend()
    docx_path = FIXTURES_DIR / "hello.docx"
    assert backend.supports(docx_path)
    assert backend.extract_text(docx_path).strip() == "Hello DOCX"

