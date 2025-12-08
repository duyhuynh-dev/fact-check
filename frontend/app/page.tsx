"use client";

import { useState, useRef, useEffect } from "react";
import Header from "@/components/Header";
import UploadSection from "@/components/UploadSection";
import ResultsSection from "@/components/ResultsSection";

function getApiBase() {
  if (typeof window !== "undefined") {
    // Client-side: use environment variable or fallback
    return process.env.NEXT_PUBLIC_API_URL || "";
  }
  return "";
}

export default function Home() {
  const [apiBase, setApiBase] = useState("");

  useEffect(() => {
    // Set API base on client side
    const base = getApiBase();
    console.log("API Base from env:", process.env.NEXT_PUBLIC_API_URL);
    console.log("API Base resolved:", base);
    if (!base) {
      console.error("NEXT_PUBLIC_API_URL is not set!");
      console.error(
        "Available env vars:",
        Object.keys(process.env).filter((k) => k.startsWith("NEXT_PUBLIC"))
      );
    }
    setApiBase(base);
  }, []);
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
    if (!apiBase) {
      console.error("API base not set");
      return;
    }
    try {
      // Load document info
      const docResponse = await fetch(`${apiBase}/v1/documents/${documentId}`);
      if (!docResponse.ok) throw new Error("Failed to load document");
      const docData = await docResponse.json();
      setDocumentData(docData);

      // Load results
      const resultsResponse = await fetch(
        `${apiBase}/v1/documents/${documentId}/results`
      );
      if (!resultsResponse.ok) throw new Error("Failed to load results");
      const resultsData = await resultsResponse.json();
      setResults(resultsData);

      // Load claims
      const claimsResponse = await fetch(
        `${apiBase}/v1/documents/${documentId}/claims`
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
      {!apiBase ? (
        <div style={{ padding: "2rem", textAlign: "center" }}>
          <p>Loading...</p>
        </div>
      ) : !showResults ? (
        <UploadSection
          onUploadComplete={handleUploadComplete}
          apiBase={apiBase}
        />
      ) : (
        <ResultsSection
          documentData={documentData}
          results={results}
          claims={claims}
          onReset={handleReset}
          apiBase={apiBase}
        />
      )}
    </div>
  );
}

