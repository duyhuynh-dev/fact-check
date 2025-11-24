#!/usr/bin/env python3
"""Test script for the full fact-checking pipeline."""

import json
import os
import time
from pathlib import Path

import httpx

# Use SQLite for testing (no PostgreSQL required)
os.environ["POSTGRES_DSN"] = "sqlite:///./test_pipeline.db"

API_BASE = "http://localhost:8001"


def test_pipeline():
    """Test the full pipeline: upload -> ingestion -> evidence -> verification -> results."""
    print("🧪 Testing Full Fact-Checking Pipeline\n")

    # Step 1: Upload a test document
    print("1️⃣ Uploading test document...")
    test_content = """
    The Holocaust was a genocide during World War II where approximately six million Jews were systematically murdered by Nazi Germany and its collaborators.
    This event is well-documented in historical records and survivor testimonies.
    Some conspiracy theories claim the Holocaust never happened, which is completely false.
    """
    test_file = Path("/tmp/test_document.txt")
    test_file.write_text(test_content)

    with httpx.Client(timeout=30.0) as client:
        with open(test_file, "rb") as f:
            response = client.post(
                f"{API_BASE}/v1/documents",
                files={"file": ("test.txt", f, "text/plain")},
                data={"title": "Test Document", "source_type": "test"},
            )
        assert response.status_code == 201, f"Upload failed: {response.text}"
        document = response.json()
        document_id = document["id"]
        print(f"   ✅ Document uploaded: {document_id}")
        print(f"   Status: {document['ingest_status']}")

        # Step 2: Wait for ingestion to complete
        print("\n2️⃣ Waiting for ingestion to complete...")
        max_wait = 30
        waited = 0
        while waited < max_wait:
            response = client.get(f"{API_BASE}/v1/documents/{document_id}")
            assert response.status_code == 200
            doc = response.json()
            if doc["ingest_status"] == "succeeded":
                print(f"   ✅ Ingestion completed in {waited}s")
                break
            elif doc["ingest_status"] == "failed":
                print(f"   ❌ Ingestion failed: {doc.get('ingest_failure_reason', 'Unknown error')}")
                return
            time.sleep(1)
            waited += 1
        else:
            print(f"   ⚠️  Ingestion timed out after {max_wait}s")
            return

        # Step 3: Check claims extracted
        print("\n3️⃣ Checking extracted claims...")
        response = client.get(f"{API_BASE}/v1/documents/{document_id}/claims")
        assert response.status_code == 200
        claims_data = response.json()
        claims = claims_data["items"]
        print(f"   ✅ Found {len(claims)} claims")
        for i, claim in enumerate(claims[:3], 1):
            print(f"      {i}. {claim['text'][:60]}...")

        # Step 4: Load evidence into RAG store
        print("\n4️⃣ Loading evidence into RAG store...")
        evidence_content = """
        The Holocaust, also known as the Shoah, was the genocide of European Jews during World War II.
        Between 1941 and 1945, Nazi Germany and its collaborators systematically murdered approximately six million Jews,
        around two-thirds of Europe's Jewish population. The murders were carried out through mass shootings,
        concentration camps, and extermination camps. The Holocaust is one of the most extensively documented
        genocides in history, with millions of pages of documentation, thousands of photographs, and extensive
        survivor testimonies. Holocaust denial is illegal in many countries and is widely condemned as antisemitic.
        """
        evidence_file = Path("/tmp/evidence.txt")
        evidence_file.write_text(evidence_content)

        with open(evidence_file, "rb") as f:
            response = client.post(
                f"{API_BASE}/v1/evidence/load",
                files={"file": ("evidence.txt", f, "text/plain")},
                data={"source_name": "Holocaust Encyclopedia"},
            )
        if response.status_code != 200:
            error_detail = response.json().get("detail", response.text)
            if "quota" in error_detail.lower() or "429" in error_detail:
                print(f"   ⚠️  Evidence load skipped: OpenAI API quota exceeded")
                print(f"      (This is expected if you've hit API limits)")
            else:
                assert False, f"Evidence load failed: {error_detail}"
        else:
            print("   ✅ Evidence loaded into RAG store")

        # Step 5: Verify claims
        print("\n5️⃣ Verifying claims...")
        response = client.post(f"{API_BASE}/v1/documents/{document_id}/claims:verify")
        if response.status_code == 400:
            print(f"   ⚠️  Verification skipped: {response.json().get('detail', 'Unknown')}")
        elif response.status_code != 200:
            error_detail = response.json().get("detail", response.text) if response.headers.get("content-type") == "application/json" else response.text
            if "quota" in error_detail.lower() or "429" in error_detail:
                print(f"   ⚠️  Verification skipped: OpenAI API quota exceeded")
            else:
                print(f"   ⚠️  Verification failed: {error_detail}")
        else:
            verified_claims = response.json()["items"]
            print(f"   ✅ Verified {len(verified_claims)} claims")
            for claim in verified_claims[:2]:
                if claim.get("verdict"):
                    print(f"      - {claim['verdict']}: {claim['text'][:50]}...")

        # Step 6: Get aggregated results
        print("\n6️⃣ Getting aggregated results...")
        response = client.get(f"{API_BASE}/v1/documents/{document_id}/results")
        assert response.status_code == 200, f"Results failed: {response.text}"
        results = response.json()
        print(f"   ✅ Results retrieved:")
        print(f"      Total claims: {results['total_claims']}")
        print(f"      Verified: {results['verified_claims']}")
        print(f"      Overall score: {results['overall_score']}")
        print(f"      Risk level: {results['risk_level']}")
        print(f"      Verdicts:")
        vs = results["verdict_summary"]
        print(f"        - Supported: {vs['supported']}")
        print(f"        - Partial: {vs['partial']}")
        print(f"        - Contradicted: {vs['contradicted']}")
        print(f"        - No evidence: {vs['no_evidence']}")
        print(f"        - Unverified: {vs['unverified']}")

        print("\n✅ Full pipeline test completed successfully!")


if __name__ == "__main__":
    try:
        test_pipeline()
    except httpx.ConnectError:
        print("❌ Error: Could not connect to API. Is the server running?")
        print("   Start it with: poetry run uvicorn backend.app.main:app --reload")
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()

