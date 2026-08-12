import { useState, useRef } from "react";

const API_URL = "http://localhost:5000/api/analyze";

export default function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(API_URL, { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Extraction request failed");
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const getOverallConfidence = (flags = []) => {
    const highCount = flags.filter((f) => f.severity === "high").length;
    const medCount = flags.filter((f) => f.severity === "medium").length;

    if (highCount > 0) {
      return { status: "high-risk", label: "High Risk / Discrepancy Flagged", class: "confidence-red" };
    }
    if (medCount > 0) {
      return { status: "medium-risk", label: "Medium Confidence", class: "confidence-yellow" };
    }
    return { status: "clean", label: "High Confidence (Sanity Clean)", class: "confidence-green" };
  };

  const flaggedFields = new Set();
  (result?.flags || []).forEach((f) => {
    if (f.check === "low_confidence_extraction") {
      const field = f.message.split("'")[1];
      if (field) flaggedFields.add(field);
    } else if (f.check === "balance_sheet_balances") {
      flaggedFields.add("total_assets");
      flaggedFields.add("total_liabilities");
      flaggedFields.add("total_equity");
    } else if (f.check === "ebitda_exceeds_revenue") {
      flaggedFields.add("ebitda");
      flaggedFields.add("total_revenue");
    }
  });

  const confidenceBadge = result ? getOverallConfidence(result.flags) : null;

  return (
    <div className="container">
      <div className="header">
        <div className="badge-pill">⚡ FinExtract Autonomous Guardrail Agent</div>
        <h1 className="title">Financial Statement Extraction</h1>
        <p className="subtitle">
          Extract line items, audit mathematical balance sheets, and catch unit discrepancies in seconds.
        </p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <input
            type="file"
            ref={fileInputRef}
            className="hidden-input"
            accept=".pdf,.xlsx,.xlsm"
            onChange={(e) => setFile(e.target.files[0])}
          />
          <div
            className="dropzone"
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="dropzone-icon">📄</div>
            {file ? (
              <div className="file-info">
                <span>Selected:</span> {file.name}
              </div>
            ) : (
              <>
                <div className="dropzone-text">Click to browse or drop your file here</div>
                <div className="dropzone-hint">Supports PDF balance sheets, P&L extracts, or Excel financial statement sheets</div>
              </>
            )}
          </div>

          <button type="submit" className="btn-primary" disabled={!file || loading}>
            {loading ? "Extracting & Auditing Statements..." : "Analyze Financial Document"}
          </button>
        </form>

        {error && (
          <p style={{ color: "var(--danger-text)", marginTop: 16, fontSize: 14, textAlign: "center" }}>
            ⚠️ {error}
          </p>
        )}
      </div>

      {result && (
        <div className="results-grid">
          {/* Header Card with Confidence Badge */}
          <div className="card">
            <div className="card-header">
              <div>
                <span className="card-title">Statement Period:</span>
                <span className="period-tag">{result.extraction.period_label || "FY/Quarter"}</span>
              </div>
              {confidenceBadge && (
                <div className={`confidence-badge ${confidenceBadge.class}`}>
                  <span>●</span> {confidenceBadge.label}
                </div>
              )}
            </div>

            <table className="data-table">
              <thead>
                <tr>
                  <th>Financial Line Item</th>
                  <th>Extracted Value</th>
                  <th>LLM Confidence</th>
                  <th>Source Text Snippet</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(result.extraction.line_items).map(([key, item]) => {
                  const isFlagged = flaggedFields.has(key);
                  const formattedValue =
                    item.value !== null && item.value !== undefined
                      ? Number(item.value).toLocaleString()
                      : "—";

                  return (
                    <tr key={key} className={isFlagged ? "row-flagged" : ""}>
                      <td className="item-key">{key.replace(/_/g, " ")}</td>
                      <td className="item-value">{formattedValue}</td>
                      <td>
                        <span
                          style={{
                            color:
                              item.confidence > 0.8
                                ? "var(--success-text)"
                                : item.confidence > 0.5
                                ? "var(--warning-text)"
                                : "var(--danger-text)",
                            fontWeight: 700,
                          }}
                        >
                          {(item.confidence * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td>
                        <span className="snippet-box" title={item.source_snippet}>
                          {item.source_snippet || "N/A"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Guardrail Audit Flags Section */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Sanity & Guardrail Audit Flags ({result.flags.length})</span>
            </div>

            {result.flags.length === 0 ? (
              <p style={{ color: "var(--success-text)", fontSize: 14, fontWeight: 600 }}>
                ✅ All mathematical & sanity guardrails passed cleanly.
              </p>
            ) : (
              <div className="flag-list">
                {result.flags.map((f, i) => (
                  <div
                    key={i}
                    className={`flag-item ${
                      f.severity === "high" ? "flag-high" : "flag-medium"
                    }`}
                  >
                    <span className="severity-pill">{f.severity}</span>
                    <div>{f.message}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
