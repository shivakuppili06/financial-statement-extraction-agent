import { useState, useRef } from "react";

const API_BASE = "http://127.0.0.1:5000";

export default function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [jobStatus, setJobStatus] = useState("");
  const [auditLog, setAuditLog] = useState([]);
  const [fieldCorrections, setFieldCorrections] = useState({});
  const fileInputRef = useRef(null);

  const handleCorrection = (key, value) => {
    setFieldCorrections(prev => ({ ...prev, [key]: value }));
    setAuditLog(prev => [...prev, { timestamp: new Date().toISOString(), action: "CORRECT", field: key, value }]);
  };

  const handleApprove = (key) => {
    setAuditLog(prev => [...prev, { timestamp: new Date().toISOString(), action: "APPROVE", field: key }]);
  };

  const handleReject = (key) => {
    setAuditLog(prev => [...prev, { timestamp: new Date().toISOString(), action: "REJECT", field: key }]);
  };

  const exportCSV = () => {
    if (!result?.extraction?.line_items) return;
    const rows = [["Field", "Original Value", "Corrected Value", "Confidence", "Status"]];
    Object.entries(result.extraction.line_items).forEach(([key, item]) => {
      const corrected = fieldCorrections[key];
      const status = auditLog.slice().reverse().find(log => log.field === key)?.action || "PENDING";
      rows.push([key, item.value, corrected || item.value, item.confidence, status]);
    });
    const csv = rows.map(r => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "powerbi_export.csv";
    a.click();
  };

  async function pollJobStatus(jobId) {
    const startTime = Date.now();
    while (Date.now() - startTime < 60000) {
      try {
        const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
        const data = await res.json();
        if (data.status === "completed") {
          setResult(data.result);
          setJobStatus("Extraction & Audit Completed!");
          setLoading(false);
          return;
        } else if (data.status === "failed") {
          setError(data.error || "Job processing failed");
          setLoading(false);
          return;
        } else {
          setJobStatus(`Background Processing... (${data.status})`);
        }
      } catch (e) {
        console.error("Polling error:", e);
      }
      await new Promise((r) => setTimeout(r, 1000));
    }
    setError("Job polling timed out.");
    setLoading(false);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setJobStatus("Submitting document to async queue...");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/api/jobs`, { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Submission failed");

      if (data.cached && data.extraction) {
        setResult({ extraction: data.extraction, flags: data.flags });
        setJobStatus("Loaded instant SHA-256 cached result ⚡");
        setLoading(false);
      } else if (data.job_id) {
        setJobStatus(`Job ${data.job_id.substring(0, 8)}... queued`);
        await pollJobStatus(data.job_id);
      }
    } catch (err) {
      setError(err.message);
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
          <div className="dropzone" onClick={() => fileInputRef.current?.click()}>
            <div className="dropzone-icon">📄</div>
            {file ? (
              <div className="file-info">
                <span>Selected:</span> {file.name}
              </div>
            ) : (
              <div>
                <div className="dropzone-text">Click to browse or drop your financial statement here</div>
                <div className="dropzone-hint">Supports PDF balance sheets, P&L extracts, or Excel financial statement sheets</div>
              </div>
            )}
          </div>

          <button type="submit" className="btn-primary" disabled={!file || loading}>
            {loading ? "Processing Document..." : "Analyze Financial Document"}
          </button>
        </form>

        {loading && jobStatus && (
          <div className="job-status-banner">
            ⏳ {jobStatus}
          </div>
        )}

        {error && (
          <p style={{ color: "var(--danger-text)", marginTop: 16, fontSize: 14, textAlign: "center" }}>
            ⚠️ {error}
          </p>
        )}
      </div>

      {result && (
        <div className="results-grid">
          <div className="card">
            <div className="card-header">
              <div>
                <span className="card-title">Statement Period:</span>
                <span className="period-tag">{result.extraction?.period_label || "FY/Quarter"}</span>
              </div>
              {confidenceBadge && (
                <div className={`confidence-badge ${confidenceBadge.class}`}>
                  <span>●</span> {confidenceBadge.label}
                </div>
              )}
            </div>
            
            <div style={{ padding: "0 20px 20px", display: "flex", gap: "10px" }}>
              <button onClick={exportCSV} className="btn-secondary" style={{ padding: "8px 16px", borderRadius: "6px", background: "var(--bg-secondary)", border: "1px solid var(--border-color)", cursor: "pointer", color: "white" }}>
                📊 Export PowerBI CSV
              </button>
            </div>

            <table className="data-table">
              <thead>
                <tr>
                  <th>Financial Line Item</th>
                  <th>Extracted Value</th>
                  <th>LLM Confidence</th>
                  <th>Source Text Snippet</th>
                  <th>Human Review</th>
                </tr>
              </thead>
              <tbody>
                {result.extraction?.line_items && Object.entries(result.extraction.line_items).map(([key, item]) => {
                  const isFlagged = flaggedFields.has(key);
                  const currentValue = fieldCorrections[key] !== undefined ? fieldCorrections[key] : item.value;
                  const formattedValue =
                    currentValue !== null && currentValue !== undefined
                      ? Number(currentValue).toLocaleString()
                      : "—";
                  
                  const latestAction = auditLog.slice().reverse().find(log => log.field === key)?.action;

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
                      <td>
                        <div style={{ display: "flex", gap: "4px", flexDirection: "column" }}>
                          {latestAction === "APPROVE" ? (
                            <span style={{ color: "var(--success-text)", fontSize: "12px" }}>✅ Approved</span>
                          ) : latestAction === "REJECT" ? (
                            <span style={{ color: "var(--danger-text)", fontSize: "12px" }}>❌ Rejected</span>
                          ) : (
                            <div style={{ display: "flex", gap: "4px" }}>
                              <button onClick={() => handleApprove(key)} style={{ padding: "2px 6px", fontSize: "12px", background: "transparent", border: "1px solid var(--success-text)", color: "var(--success-text)", borderRadius: "4px", cursor: "pointer" }}>Approve</button>
                              <button onClick={() => handleReject(key)} style={{ padding: "2px 6px", fontSize: "12px", background: "transparent", border: "1px solid var(--danger-text)", color: "var(--danger-text)", borderRadius: "4px", cursor: "pointer" }}>Reject</button>
                            </div>
                          )}
                          <input 
                            type="number" 
                            placeholder="Correct..." 
                            onBlur={(e) => e.target.value && handleCorrection(key, e.target.value)}
                            style={{ padding: "2px", fontSize: "12px", width: "80px", background: "transparent", border: "1px solid var(--border-color)", color: "white" }} 
                          />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">Sanity & Guardrail Audit Flags ({result.flags?.length || 0})</span>
            </div>

            {result.flags?.length === 0 ? (
              <p style={{ color: "var(--success-text)", fontSize: 14, fontWeight: 600 }}>
                ✅ All mathematical & sanity guardrails passed cleanly.
              </p>
            ) : (
              <div className="flag-list">
                {result.flags?.map((f, i) => (
                  <div
                    key={i}
                    className={`flag-item ${f.severity === "high" ? "flag-high" : "flag-medium"}`}
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
