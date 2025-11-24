"""Background task helpers for ingestion."""

from pathlib import Path

from sqlmodel import Session

from sqlmodel import select

from backend.app.core.config import get_settings
from backend.app.db.models import Claim, Document
from backend.app.db.session import get_engine
from backend.app.services.claims import ClaimService
from backend.app.services.ingestion import (
    IngestionService,
    create_default_ingestion_service,
)
from backend.app.services.verification import create_verifier


def run_ingestion_job(
    document_id: str,
    service: IngestionService | None = None,
) -> None:
    """Process a document: OCR + normalized text persistence."""
    ingestion_service = service or create_default_ingestion_service()

    with Session(get_engine()) as session:
        document = session.get(Document, document_id)
        if document is None:
            return

        try:
            text = ingestion_service.run_ocr(Path(document.raw_path))
            text_path = ingestion_service.persist_text(text, document)
            document.text_path = str(text_path)
            document.ingest_status = "succeeded"
            document.ingest_failure_reason = None
            ClaimService().extract_for_document(session, document)

            # Verify claims (works in free mode too)
            verifier = create_verifier()
            claims = session.exec(select(Claim).where(Claim.document_id == document.id)).all()
            for claim in claims:
                try:
                    verifier.verify(claim, session)
                except Exception:
                    pass  # Skip failed verifications, don't break ingestion
        except Exception as exc:  # broad catch to mark failure
            document.ingest_status = "failed"
            document.ingest_failure_reason = str(exc)
        finally:
            session.add(document)
            session.commit()

