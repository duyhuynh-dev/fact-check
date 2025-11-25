"""Background task helpers for ingestion."""

import logging
from pathlib import Path

from sqlmodel import Session, select

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
    """Process a document: OCR + normalized text persistence with progress tracking."""
    logger = logging.getLogger(__name__)
    logger.info("Starting ingestion job for document %s", document_id)
    ingestion_service = service or create_default_ingestion_service()

    def update_progress(progress: float, message: str) -> None:
        """Update document progress in database."""
        with Session(get_engine()) as session:
            doc = session.get(Document, document_id)
            if doc:
                doc.ingest_progress = progress
                doc.ingest_progress_message = message
                session.add(doc)
                session.commit()

    with Session(get_engine()) as session:
        document = session.get(Document, document_id)
        if document is None:
            return

        try:
            document.ingest_status = "processing"
            document.ingest_progress = 0.0
            document.ingest_progress_message = "Starting OCR..."
            session.add(document)
            session.commit()

            # Check document size before processing
            file_path = Path(document.raw_path)
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            
            # Warn for very large files
            if file_size_mb > 100:
                update_progress(0.0, f"Large file detected ({file_size_mb:.1f} MB). Processing may take a long time...")
            
            # OCR with progress tracking
            update_progress(0.1, "Extracting text from document...")
            progress_cb = lambda p, msg: update_progress(0.1 + p * 0.3, msg)
            try:
                text = ingestion_service.run_ocr(
                    file_path,
                    progress_callback=progress_cb,
                )
            except TypeError as type_err:
                # Fallback for ingestion services that don't support progress callbacks yet
                if "progress_callback" in str(type_err):
                    text = ingestion_service.run_ocr(file_path)
                else:
                    raise
            except MemoryError:
                raise ValueError(
                    "Document is too large to process. Try splitting into smaller files (recommended: <500 pages)."
                )
            except Exception as e:
                if "memory" in str(e).lower() or "too large" in str(e).lower():
                    raise ValueError(
                        f"Document too large: {str(e)}. Try splitting into smaller files."
                    )
                raise
            
            update_progress(0.4, "Saving extracted text...")
            text_path = ingestion_service.persist_text(text, document)
            document.text_path = str(text_path)
            
            update_progress(0.5, "Extracting claims...")
            claims = ClaimService().extract_for_document(session, document)
            document.ingest_progress = 0.6
            document.ingest_progress_message = f"Extracted {len(claims)} claims. Verifying..."
            session.add(document)
            session.commit()

            # Verify claims in batches (for large documents)
            verifier = create_verifier()
            total_claims = len(claims)
            verified_count = 0
            
            # For very large documents, skip semantic analysis to speed up
            settings = get_settings()
            skip_semantic = total_claims > 100  # Skip for 100+ claims
            
            # PRE-VERIFICATION: Check for antisemitic content BEFORE calling verifier
            # This ensures we catch antisemitic content even if verifier fails
            from backend.app.services.semantic_analysis import create_semantic_analyzer
            semantic_analyzer = create_semantic_analyzer()
            
            for i, claim in enumerate(claims):
                try:
                    # Update progress
                    if i % 10 == 0 or i == total_claims - 1:
                        progress = 0.6 + (i / total_claims) * 0.35
                        update_progress(progress, f"Verifying claim {i+1}/{total_claims}...")
                    
                    # STEP 1: Pre-check for antisemitic content using semantic analysis
                    # This runs BEFORE the verifier to catch antisemitic content early
                    try:
                        sem_result = semantic_analyzer.analyze(claim.text)
                        if sem_result.is_antisemitic and sem_result.confidence > 0.5:  # Lower threshold for pre-check
                            # Flag as antisemitic immediately
                            claim.verdict = "antisemitic_trope"
                            patterns = sem_result.detected_patterns or []
                            rationale_parts = [
                                f"This content is antisemitic. {sem_result.explanation or 'Content contains antisemitic messaging.'}",
                            ]
                            
                            # Add tone analysis if available
                            if sem_result.tone:
                                rationale_parts.append(f"Tone: {sem_result.tone}")
                            if sem_result.emotional_weight:
                                rationale_parts.append(f"Emotional weight: {sem_result.emotional_weight}")
                            if sem_result.intent:
                                rationale_parts.append(f"Intent: {sem_result.intent}")
                            if patterns:
                                rationale_parts.append(f"Detected patterns: {', '.join(patterns)}")
                            if sem_result.implicit_meaning:
                                rationale_parts.append(f"Implicit meaning: {sem_result.implicit_meaning}")
                            
                            claim.rationale = ". ".join([p for p in rationale_parts if p])
                            claim.score = None
                            if claim.metadata_json is None:
                                claim.metadata_json = {}
                            claim.metadata_json["semantic_analysis"] = {
                                "is_antisemitic": sem_result.is_antisemitic,
                                "confidence": sem_result.confidence,
                                "detected_patterns": patterns,
                                "explanation": sem_result.explanation,
                                "coded_language_detected": sem_result.coded_language_detected,
                                "implicit_meaning": sem_result.implicit_meaning,
                                "tone": sem_result.tone,
                                "emotional_weight": sem_result.emotional_weight,
                                "intent": sem_result.intent,
                            }
                            claim.metadata_json["antisemitic_trope_detected"] = True
                            claim.metadata_json["trope_patterns"] = patterns
                            claim.metadata_json["pre_verification_detection"] = True
                            session.add(claim)
                            session.commit()
                            session.refresh(claim)
                            verified_count += 1
                            continue  # Skip verifier, already flagged
                    except Exception as sem_error:
                        # If semantic analysis fails, continue to verifier
                        pass
                    
                    # STEP 2: Run verifier (which also does LLM analysis)
                    verifier.verify(claim, session)
                    verified_count += 1
                except Exception as e:
                    # If verification fails completely, mark as no_evidence but log error
                    if claim.verdict is None or claim.verdict == "unverified":
                        claim.verdict = "no_evidence"
                        claim.rationale = f"Verification failed: {str(e)[:200]}"
                        claim.score = 50.0
                        if claim.metadata_json is None:
                            claim.metadata_json = {}
                        claim.metadata_json["verification_error"] = str(e)
                        session.add(claim)
                        session.commit()
                    verified_count += 1

            document.ingest_status = "succeeded"
            document.ingest_failure_reason = None
            document.ingest_progress = 1.0
            document.ingest_progress_message = f"Complete: {verified_count}/{total_claims} claims verified"
        except Exception as exc:  # broad catch to mark failure
            document.ingest_status = "failed"
            document.ingest_failure_reason = str(exc)
            document.ingest_progress = None
            document.ingest_progress_message = f"Failed: {str(exc)[:100]}"
            logger.exception("Ingestion job failed for document %s: %s", document_id, exc)
        finally:
            session.add(document)
            session.commit()
            logger.info(
                "Ingestion job completed with status %s for document %s",
                document.ingest_status,
                document_id,
            )

