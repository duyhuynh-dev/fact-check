"use client";

interface ResultsSectionProps {
  documentData: any;
  results: any;
  claims: any[];
  onReset: () => void;
  apiBase: string;
}

export default function ResultsSection({
  documentData,
  results,
  claims,
  onReset,
  apiBase,
}: ResultsSectionProps) {
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
