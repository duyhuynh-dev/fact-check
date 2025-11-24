import os
from pathlib import Path

os.environ["POSTGRES_DSN"] = "sqlite:///./tests/test.db"
os.environ["INGEST_BUCKET_PATH"] = "./data/test-uploads"
os.environ["PROCESSED_TEXT_PATH"] = "./data/test-processed"
os.environ["CLAIM_EXTRACTOR"] = "simple"
FIXTURES_DIR = Path(__file__).parent

from backend.app.core.config import get_settings

get_settings.cache_clear()


from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, select

from backend.app.db.models import Claim
from backend.app.db.session import get_engine
from backend.app.main import app


def setup_module() -> None:
    SQLModel.metadata.create_all(bind=get_engine())
    Path("./data/test-uploads").mkdir(parents=True, exist_ok=True)
    Path("./data/test-processed").mkdir(parents=True, exist_ok=True)


def teardown_module() -> None:
    SQLModel.metadata.drop_all(bind=get_engine())


client = TestClient(app)


def _get_claims(document_id: str) -> list[Claim]:
    with Session(get_engine()) as session:
        return session.exec(select(Claim).where(Claim.document_id == document_id)).all()


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_document_upload_and_fetch() -> None:
    response = client.post(
        "/v1/documents",
        files={"file": ("sample.txt", b"test content", "text/plain")},
        data={"title": "Sample"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Sample"
    document_id = payload["id"]

    detail_response = client.get(f"/v1/documents/{document_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == document_id
    assert detail["ingest_status"] == "succeeded"
    assert detail["text_path"]
    assert Path(detail["text_path"]).read_text() == "test content"

    claims_resp = client.get(f"/v1/documents/{document_id}/claims")
    assert claims_resp.status_code == 200
    claims = claims_resp.json()["items"]
    assert isinstance(claims, list) and len(claims) >= 1

    reextract_resp = client.post(f"/v1/documents/{document_id}/claims:reextract")
    assert reextract_resp.status_code == 200
    claims = _get_claims(document_id)
    assert claims


def test_document_upload_failure_for_unknown_extension() -> None:
    response = client.post(
        "/v1/documents",
        files={"file": ("sample.bin", b"\x00\x01", "application/octet-stream")},
    )
    assert response.status_code == 201
    document_id = response.json()["id"]

    detail_response = client.get(f"/v1/documents/{document_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["ingest_status"] == "failed"
    failure = detail["ingest_failure_reason"] or ""
    assert "OCR backend" in failure


def test_pdf_upload_pipeline() -> None:
    pdf_path = FIXTURES_DIR / "hello.pdf"
    response = client.post(
        "/v1/documents",
        files={"file": (pdf_path.name, pdf_path.read_bytes(), "application/pdf")},
    )
    assert response.status_code == 201
    document_id = response.json()["id"]

    detail = client.get(f"/v1/documents/{document_id}").json()
    assert detail["ingest_status"] == "succeeded"
    normalized_text = Path(detail["text_path"]).read_text().strip()
    assert normalized_text == "Hello PDF"
    claims = _get_claims(document_id)
    assert claims


def test_docx_upload_pipeline() -> None:
    docx_path = FIXTURES_DIR / "hello.docx"
    response = client.post(
        "/v1/documents",
        files={"file": (docx_path.name, docx_path.read_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 201
    document_id = response.json()["id"]

    detail = client.get(f"/v1/documents/{document_id}").json()
    assert detail["ingest_status"] == "succeeded"
    normalized_text = Path(detail["text_path"]).read_text().strip()
    assert normalized_text == "Hello DOCX"
    claims = _get_claims(document_id)
    assert claims

