"""Document ingestion API routes."""

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlmodel import Session, select

import logging

from backend.app.db.models import Document
from backend.app.db.session import get_session
from backend.app.models.claims import ClaimList, ClaimRead
from backend.app.models.documents import DocumentList, DocumentRead
from backend.app.models.results import DocumentResults, VerdictSummary
from backend.app.core.config import get_settings
from backend.app.services.ingestion import IngestionService, create_default_ingestion_service
from backend.app.worker.queue import JobQueue, resolve_job_queue
from backend.app.services.claims import ClaimService
from backend.app.services.verification import ClaimVerifier, create_verifier
from backend.app.db.models import Claim

router = APIRouter(prefix="/v1/documents", tags=["documents"])


def get_ingestion_service() -> IngestionService:
    """Instantiate the ingestion service with default OCR backend."""
    return create_default_ingestion_service()


def get_job_queue() -> JobQueue:
    return resolve_job_queue()


def get_claim_service() -> ClaimService:
    return ClaimService()


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document for fact-checking",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF, DOCX, image (PNG/JPG/GIF/WEBP), or text file."),
    title: str | None = Form(default=None),
    source_type: str = Form(default="upload"),
    session: Session = Depends(get_session),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    job_queue: JobQueue = Depends(get_job_queue),
) -> DocumentRead:
    """Accept a document upload, store the artifact, and create a DB record."""
    import logging
    import asyncio
    logger = logging.getLogger(__name__)
    
    # File size limit: 100MB
    MAX_FILE_SIZE = 100 * 1024 * 1024
    
    try:
        logger.info(f"Received upload request: filename={file.filename}, title={title}")
        
        # Read file with size check
        file_bytes = await file.read()
        file_size = len(file_bytes)
        logger.info(f"File read successfully, size: {file_size} bytes")
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB"
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        # Store file
        stored_path = ingestion_service.store_raw(file_bytes, file.filename)
        logger.info(f"File stored at: {stored_path}")

        # Create document record
        document = Document(
            title=title or file.filename,
            source_type=source_type,
            raw_path=str(stored_path),
            ingest_status="processing",
        )
        session.add(document)
        session.commit()
        session.refresh(document)
        logger.info(f"Document created with ID: {document.id}")

        # Enqueue job (non-blocking, fire and forget)
        try:
            # Don't await - let it run in background to avoid timeout
            asyncio.create_task(job_queue.enqueue(document.id))
            logger.info(f"Job enqueued for document {document.id}")
        except Exception as job_error:
            logger.error(f"Failed to enqueue job for document {document.id}: {str(job_error)}")
            # Don't fail the upload if job enqueue fails - job can be retried later
        
        return DocumentRead.model_validate(document)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}", exc_info=True)
        try:
            session.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )


@router.get(
    "/{document_id}/claims",
    response_model=ClaimList,
    summary="List claims extracted for a document",
)
def list_claims(
    document_id: str,
    session: Session = Depends(get_session),
) -> ClaimList:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    claims = session.exec(select(Claim).where(Claim.document_id == document_id)).all()
    return ClaimList(items=[ClaimRead.model_validate(c) for c in claims])


@router.post(
    "/{document_id}/claims:reextract",
    response_model=ClaimList,
    summary="Re-run claim extraction for a document",
)
def reextract_claims(
    document_id: str,
    session: Session = Depends(get_session),
    claim_service: ClaimService = Depends(get_claim_service),
) -> ClaimList:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    claims = claim_service.extract_for_document(session, document)
    return ClaimList(items=[ClaimRead.model_validate(c) for c in claims])


@router.get(
    "",
    response_model=DocumentList,
    summary="List ingested documents",
)
def list_documents(
    limit: int = 50,
    session: Session = Depends(get_session),
) -> DocumentList:
    results = session.exec(
        select(Document).order_by(Document.created_at.desc()).limit(limit)
    ).all()
    return DocumentList(items=[DocumentRead.model_validate(doc) for doc in results])


@router.get(
    "/{document_id}",
    response_model=DocumentRead,
    summary="Fetch a single document status",
)
def get_document(
    document_id: str,
    session: Session = Depends(get_session),
) -> DocumentRead:
    logger = logging.getLogger(__name__)
    document = session.get(Document, document_id)
    if document is None:
        logger.warning("Document %s not found", document_id)
        raise HTTPException(status_code=404, detail="Document not found")
    logger.info(
        "Fetch document %s status=%s progress=%s message=%s",
        document_id,
        document.ingest_status,
        document.ingest_progress,
        document.ingest_progress_message,
    )
    return DocumentRead.model_validate(document)


@router.post(
    "/{document_id}/claims:verify",
    response_model=ClaimList,
    summary="Verify all claims for a document",
)
def verify_claims(
    document_id: str,
    session: Session = Depends(get_session),
) -> ClaimList:
    """Verify all claims for a document using LLM."""
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    claims = session.exec(select(Claim).where(Claim.document_id == document_id)).all()
    if not claims:
        raise HTTPException(status_code=404, detail="No claims found for document")

    verifier = create_verifier()
    verified = []
    for claim in claims:
        try:
            verified_claim = verifier.verify(claim, session)
            verified.append(verified_claim)
        except Exception as e:
            # Continue with other claims even if one fails
            pass

    return ClaimList(items=[ClaimRead.model_validate(c) for c in verified])


@router.get(
    "/{document_id}/results",
    response_model=DocumentResults,
    summary="Get aggregated verification results for a document",
)
def get_document_results(
    document_id: str,
    session: Session = Depends(get_session),
) -> DocumentResults:
    """Get aggregated results including overall score and verdict breakdown."""
    logger = logging.getLogger(__name__)
    document = session.get(Document, document_id)
    if document is None:
        logger.warning("Results requested for missing document %s", document_id)
        raise HTTPException(status_code=404, detail="Document not found")

    claims = session.exec(select(Claim).where(Claim.document_id == document_id)).all()
    total_claims = len(claims)

    if total_claims == 0:
        return DocumentResults(
            document_id=document_id,
            total_claims=0,
            verified_claims=0,
            overall_score=None,
            verdict_summary=VerdictSummary(),
            risk_level="unknown",
        )

    # Count verdicts
    verdict_counts = {
        "supported": 0,
        "partial": 0,
        "contradicted": 0,
        "no_evidence": 0,
        "not_applicable": 0,
        "antisemitic_trope": 0,
        "unverified": 0,
    }

    scores = []
    for claim in claims:
        if claim.verdict:
            verdict_counts[claim.verdict] = verdict_counts.get(claim.verdict, 0) + 1
            # Only include scores from factual claims (exclude not_applicable and antisemitic_trope)
            if claim.score is not None and claim.verdict not in ["not_applicable", "antisemitic_trope"]:
                scores.append(claim.score)
        else:
            verdict_counts["unverified"] += 1

    # Calculate overall score (average of factual claim scores only, excluding not_applicable)
    overall_score = sum(scores) / len(scores) if scores else None

    # Determine risk level
    if overall_score is None:
        risk_level = "unknown"
    elif overall_score >= 70:
        risk_level = "low"
    elif overall_score >= 40:
        risk_level = "medium"
    else:
        risk_level = "high"

    verified_claims = total_claims - verdict_counts["unverified"]
    results = DocumentResults(
        document_id=document_id,
        total_claims=total_claims,
        verified_claims=verified_claims,
        overall_score=round(overall_score, 2) if overall_score is not None else None,
        verdict_summary=VerdictSummary(
            supported=verdict_counts["supported"],
            partial=verdict_counts["partial"],
            contradicted=verdict_counts["contradicted"],
            no_evidence=verdict_counts["no_evidence"],
            not_applicable=verdict_counts["not_applicable"],
            antisemitic_trope=verdict_counts["antisemitic_trope"],
            unverified=verdict_counts["unverified"],
        ),
        risk_level=risk_level,
    )
    logger.info(
        "Results prepared for document %s: total_claims=%s verified=%s score=%s",
        document_id,
        total_claims,
        verified_claims,
        results.overall_score,
    )
    return results

