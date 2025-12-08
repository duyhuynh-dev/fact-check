"use client";

import { useState, useRef, useEffect } from "react";
import Header from "@/components/Header";
import UploadSection from "@/components/UploadSection";
import ResultsSection from "@/components/ResultsSection";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" ? window.location.origin : "");

export default function Home() {
  const [currentDocumentId, setCurrentDocumentId] = useState<string | null>(
    null
  );
  const [showResults, setShowResults] = useState(false);
  const [documentData, setDocumentData] = useState<any>(null);
  const [results, setResults] = useState<any>(null);
  const [claims, setClaims] = useState<any[]>([]);

  const handleUploadComplete = (documentId: string) => {
    setCurrentDocumentId(documentId);
    setShowResults(true);
    loadResults(documentId);
  };

  const loadResults = async (documentId: string) => {
    try {
      // Load document info
      const docResponse = await fetch(`${API_BASE}/v1/documents/${documentId}`);
      if (!docResponse.ok) throw new Error("Failed to load document");
      const docData = await docResponse.json();
      setDocumentData(docData);

      // Load results
      const resultsResponse = await fetch(
        `${API_BASE}/v1/documents/${documentId}/results`
      );
      if (!resultsResponse.ok) throw new Error("Failed to load results");
      const resultsData = await resultsResponse.json();
      setResults(resultsData);

      // Load claims
      const claimsResponse = await fetch(
        `${API_BASE}/v1/documents/${documentId}/claims`
      );
      if (!claimsResponse.ok) throw new Error("Failed to load claims");
      const claimsData = await claimsResponse.json();
      setClaims(claimsData.items || []);
    } catch (error) {
      console.error("Error loading results:", error);
      alert(
        `Error loading results: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    }
  };

  const handleReset = () => {
    setCurrentDocumentId(null);
    setShowResults(false);
    setDocumentData(null);
    setResults(null);
    setClaims([]);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="container">
      <Header />
      {!showResults ? (
        <UploadSection
          onUploadComplete={handleUploadComplete}
          apiBase={API_BASE}
        />
      ) : (
        <ResultsSection
          documentData={documentData}
          results={results}
          claims={claims}
          onReset={handleReset}
        />
      )}
    </div>
  );
}
