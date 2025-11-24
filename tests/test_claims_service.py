from pathlib import Path
from unittest.mock import MagicMock, patch

from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.db.models import Claim, Document
from backend.app.services.claims import (
    ClaimService,
    LLMClaimExtractor,
    SimpleSentenceExtractor,
)

test_engine = create_engine("sqlite://")


def setup_module() -> None:
    SQLModel.metadata.create_all(bind=test_engine)


def teardown_module() -> None:
    SQLModel.metadata.drop_all(bind=test_engine)


def test_simple_extractor_splits_sentences() -> None:
    extractor = SimpleSentenceExtractor()
    text = "Sentence one is informative. Short. Another claim appears here!"
    claims = extractor.extract(text)
    assert len(claims) >= 2
    assert claims[0].text.startswith("Sentence one")


def test_claim_extraction_service_persists_claims(tmp_path: Path) -> None:
    text_path = tmp_path / "doc.txt"
    text_path.write_text("Fact one is stated here. Another fact is there.", encoding="utf-8")

    with Session(test_engine) as session:
        document = Document(
            title="Test Doc",
            source_type="upload",
            raw_path=str(text_path),
            text_path=str(text_path),
            ingest_status="succeeded",
        )
        session.add(document)
        session.commit()
        session.refresh(document)

        service = ClaimService()
        persisted = service.extract_for_document(session, document)

        assert len(persisted) >= 2
        stored_claims = session.exec(select(Claim).where(Claim.document_id == document.id)).all()
        assert stored_claims


def test_llm_extractor_with_mock() -> None:
    """Test LLM extractor with mocked OpenAI client."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='{"claims": [{"text": "Test claim one", "span_start": 0, "span_end": 15}, {"text": "Test claim two", "span_start": 16, "span_end": 30}]}'
            )
        )
    ]

    with patch("openai.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        extractor = LLMClaimExtractor(model="gpt-4o-mini", api_key="test-key")
        candidates = extractor.extract("Test claim one. Test claim two.")

        assert len(candidates) == 2
        assert candidates[0].text == "Test claim one"
        assert candidates[0].metadata["strategy"] == "llm_openai"
        assert candidates[0].metadata["model"] == "gpt-4o-mini"

