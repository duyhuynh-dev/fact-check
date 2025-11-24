"""Evidence/RAG API routes."""

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from backend.app.core.config import get_settings
from backend.app.services.rag import EvidenceRetriever, create_default_evidence_retriever

router = APIRouter(prefix="/v1/evidence", tags=["evidence"])


def get_evidence_retriever() -> EvidenceRetriever:
    """Dependency for evidence retriever."""
    return create_default_evidence_retriever()


@router.post(
    "/load",
    status_code=status.HTTP_200_OK,
    summary="Load evidence document into RAG store",
)
async def load_evidence(
    file: UploadFile = File(..., description="Text file containing evidence."),
    source_name: str = Form(..., description="Name of the evidence source."),
    evidence_retriever: EvidenceRetriever = Depends(get_evidence_retriever),
) -> dict:
    """Load a text file into the RAG vector store for evidence retrieval.
    
    Uses free local embeddings (sentence-transformers) if OPENAI_API_KEY is not set.
    """

    # Save uploaded file temporarily
    file_bytes = await file.read()
    temp_path = Path(f"/tmp/{file.filename}")
    temp_path.write_bytes(file_bytes)

    try:
        evidence_retriever.load_from_file(temp_path, source_name)
        return {
            "status": "loaded",
            "source_name": source_name,
            "filename": file.filename,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load evidence: {str(e)}",
        )
    finally:
        if temp_path.exists():
            temp_path.unlink()

