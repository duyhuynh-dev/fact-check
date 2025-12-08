"use client";

import { useState, useRef } from "react";

interface UploadSectionProps {
  onUploadComplete: (documentId: string) => void;
  apiBase: string;
}

export default function UploadSection({
  onUploadComplete,
  apiBase,
}: UploadSectionProps) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressText, setProgressText] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const checkIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const handleFileSelect = (file: File) => {
    if (!file.name.match(/\.(pdf|docx|txt|png|jpg|jpeg|gif|webp|bmp)$/i)) {
      alert(
        "Please upload a PDF, DOCX, TXT, or image file (PNG, JPG, GIF, WEBP, BMP)"
      );
      return;
    }

    handleFile(file);
  };

  const handleFile = async (file: File) => {
    setUploading(true);
    setProgress(10);
    setProgressText("Uploading document...");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", file.name);
      formData.append("source_type", "upload");

      setProgress(30);
      setProgressText("Sending to server...");

      if (!apiBase) {
        throw new Error(
          "API URL not configured. Please set NEXT_PUBLIC_API_URL in Vercel."
        );
      }

      console.log("Uploading to:", `${apiBase}/v1/documents`);
      const response = await fetch(`${apiBase}/v1/documents`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const document = await response.json();
      setProgress(50);
      setProgressText("Processing document...");
      await waitForIngestion(document.id);
    } catch (error) {
      console.error("Upload error:", error);
      console.error("API Base URL:", apiBase);
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";
      if (errorMessage.includes("Failed to fetch")) {
        alert(
          `Connection failed. Check:\n1. NEXT_PUBLIC_API_URL is set in Vercel\n2. Backend is running at ${
            apiBase || "not set"
          }\n3. CORS is configured on backend`
        );
      } else {
        alert(`Error: ${errorMessage}`);
      }
      setUploading(false);
      setProgress(0);
    }
  };

  const waitForIngestion = (documentId: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      let attempts = 0;
      const maxAttempts = 60;

      setProgress(60);
      setProgressText("Extracting claims...");

      checkIntervalRef.current = setInterval(async () => {
        attempts++;

        try {
          const response = await fetch(`${apiBase}/v1/documents/${documentId}`);
          if (!response.ok) throw new Error("Failed to check status");

          const doc = await response.json();

          if (doc.ingest_status === "succeeded") {
            if (checkIntervalRef.current) {
              clearInterval(checkIntervalRef.current);
            }
            setProgress(80);
            setProgressText("Loading evidence...");
            await loadEvidence();
            setProgress(90);
            setProgressText("Verifying claims...");
            await verifyClaims(documentId);
            setProgress(100);
            setProgressText("Complete!");
            setTimeout(() => {
              onUploadComplete(documentId);
              resolve();
            }, 500);
          } else if (doc.ingest_status === "failed") {
            if (checkIntervalRef.current) {
              clearInterval(checkIntervalRef.current);
            }
            throw new Error(doc.ingest_failure_reason || "Ingestion failed");
          } else if (attempts >= maxAttempts) {
            if (checkIntervalRef.current) {
              clearInterval(checkIntervalRef.current);
            }
            throw new Error("Processing timeout");
          } else {
            const progressValue =
              doc.ingest_progress !== null
                ? 60 + doc.ingest_progress * 30
                : 60 + attempts * 0.3;
            setProgress(progressValue);
            setProgressText(doc.ingest_progress_message || "Processing...");
          }
        } catch (error) {
          if (checkIntervalRef.current) {
            clearInterval(checkIntervalRef.current);
          }
          reject(error);
        }
      }, 1000);
    });
  };

  const loadEvidence = async () => {
    const evidenceContent = `The Holocaust, also known as the Shoah, was the genocide of European Jews during World War II.
Between 1941 and 1945, Nazi Germany and its collaborators systematically murdered approximately six million Jews,
around two-thirds of Europe's Jewish population. The murders were carried out through mass shootings,
concentration camps, and extermination camps. The Holocaust is one of the most extensively documented
genocides in history, with millions of pages of documentation, thousands of photographs, and extensive
survivor testimonies. Holocaust denial is illegal in many countries and is widely condemned as antisemitic.`;

    const blob = new Blob([evidenceContent], { type: "text/plain" });
    const formData = new FormData();
    formData.append("file", blob, "evidence.txt");
    formData.append("source_name", "Holocaust Encyclopedia");

    try {
      await fetch(`${apiBase}/v1/evidence/load`, {
        method: "POST",
        body: formData,
      });
    } catch (error) {
      console.warn("Evidence loading failed:", error);
    }
  };

  const verifyClaims = async (documentId: string) => {
    try {
      await fetch(`${apiBase}/v1/documents/${documentId}/claims:verify`, {
        method: "POST",
      });
    } catch (error) {
      console.warn("Verification failed:", error);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  return (
    <section className="hero" id="upload">
      <h1 className="hero-title">
        <span className="title-line">Verify</span>
        <span className="title-line">Antisemitism-Related</span>
        <span className="title-line highlight">Claims</span>
      </h1>
      <p className="hero-subtitle">
        Upload documents or screenshots to verify.
      </p>

      <div className="upload-section">
        {!uploading ? (
          <div
            className="upload-box"
            onClick={() => fileInputRef.current?.click()}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.gif,.webp,.bmp"
              style={{ display: "none" }}
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0) {
                  handleFileSelect(e.target.files[0]);
                }
              }}
            />
            <div className="upload-content">
              <svg
                className="upload-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
              <p className="upload-text">
                Drop your document or screenshot here or click to browse
              </p>
              <p className="upload-hint">
                Supports PDF, DOCX, TXT, and images (PNG, JPG, GIF, WEBP)
              </p>
            </div>
          </div>
        ) : (
          <div className="upload-progress">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
            <p className="progress-text">{progressText}</p>
          </div>
        )}
      </div>
    </section>
  );
}

