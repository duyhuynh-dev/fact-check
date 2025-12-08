"use client";

import { useEffect, useRef } from "react";

interface ResultsSectionProps {
  documentData: any;
  results: any;
  claims: any[];
  onReset: () => void;
}

export default function ResultsSection({
  documentData,
  results,
  claims,
  onReset,
}: ResultsSectionProps) {
  const scoreCircleRef = useRef<SVGCircleElement>(null);

  useEffect(() => {
    if (results?.overall_score !== null && scoreCircleRef.current) {
      const score = results.overall_score;
      const circumference = 2 * Math.PI * 45;
      const offset = circumference - (score / 100) * circumference;
      scoreCircleRef.current.style.strokeDashoffset = String(offset);
    }
  }, [results]);

  const formatVerdict = (verdict: string) => {
    if (verdict === "not_applicable") return "Not Applicable";
    if (verdict === "no_evidence") return "No Evidence";
    if (verdict === "antisemitic_trope") return "Antisemitic Trope";
    return verdict;
  };

  const escapeHtml = (text: string) => {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  };

  return (
    <section className="results-section" id="results">
      <div className="results-header">
        <h2 className="results-title">Verification Results</h2>
        <button className="btn-secondary" onClick={onReset}>
          Upload New Document
        </button>
      </div>

      {documentData && (
        <div className="document-info">
          <h3>{documentData.title || "Document"}</h3>
          <div className={`status-badge ${documentData.ingest_status}`}>
            {documentData.ingest_status}
          </div>
        </div>
      )}

      {results && (
        <>
          <div className="score-card">
            <div className="score-circle">
              <svg className="score-svg" viewBox="0 0 100 100">
                <circle className="score-bg" cx="50" cy="50" r="45"></circle>
                <circle
                  ref={scoreCircleRef}
                  className="score-fill"
                  cx="50"
                  cy="50"
                  r="45"
                ></circle>
              </svg>
              <div className="score-value">
                {results.overall_score !== null
                  ? Math.round(results.overall_score)
                  : "--"}
              </div>
            </div>
            <div className="score-info">
              <h3 className={`risk-level ${results.risk_level}`}>
                {results.risk_level || "unknown"}
              </h3>
              <p className="score-label">Overall Accuracy Score</p>
            </div>
          </div>

          {results.verdict_summary && (
            <div className="verdict-summary">
              <h3>Verdict Breakdown</h3>
              <div className="verdict-stats">
                <div className="stat-item supported">
                  <div className="stat-value">
                    {results.verdict_summary.supported}
                  </div>
                  <div className="stat-label">Supported</div>
                </div>
                <div className="stat-item partial">
                  <div className="stat-value">
                    {results.verdict_summary.partial}
                  </div>
                  <div className="stat-label">Partial</div>
                </div>
                <div className="stat-item contradicted">
                  <div className="stat-value">
                    {results.verdict_summary.contradicted}
                  </div>
                  <div className="stat-label">Contradicted</div>
                </div>
                <div className="stat-item no-evidence">
                  <div className="stat-value">
                    {results.verdict_summary.no_evidence}
                  </div>
                  <div className="stat-label">No Evidence</div>
                </div>
                <div className="stat-item not-applicable">
                  <div className="stat-value">
                    {results.verdict_summary.not_applicable || 0}
                  </div>
                  <div className="stat-label">Not Applicable</div>
                </div>
                <div className="stat-item antisemitic-trope">
                  <div className="stat-value">
                    {results.verdict_summary.antisemitic_trope || 0}
                  </div>
                  <div className="stat-label">Antisemitic Trope</div>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      <div className="claims-section">
        <h3>Extracted Claims</h3>
        <div className="claims-list">
          {claims.map((claim, index) => {
            const verdict = claim.verdict || "unverified";
            const verdictClass = verdict.replace(/_/g, "-");
            return (
              <div key={index} className="claim-card">
                <div className="claim-header">
                  <div className="claim-text">{claim.text}</div>
                  <div className={`claim-verdict ${verdictClass}`}>
                    {formatVerdict(verdict)}
                  </div>
                </div>
                <div className="claim-details">
                  <div className="claim-score">
                    Score:{" "}
                    {claim.score !== null ? Math.round(claim.score) : "N/A"}
                  </div>
                </div>
                {claim.rationale && (
                  <div
                    className="claim-rationale"
                    dangerouslySetInnerHTML={{
                      __html: escapeHtml(claim.rationale),
                    }}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
