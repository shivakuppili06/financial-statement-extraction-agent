# Financial Statement Extraction & Sanity-Check Agent

An autonomous LLM agent built with **Flask**, **Google Gemini AI**, and **React (Vite)** that parses financial statement extracts (PDFs & Excel workbooks), extracts key line items into strict JSON, and executes a multi-layer guardrail suite to detect mathematical inconsistencies, unit scaling errors, and unextracted fields.

---

## 🌟 Key Features

- **Document Processing Pipeline:** Extracts raw text & table grids from PDF balance sheets/P&L extracts (`pdfplumber`) and multi-sheet Excel files (`openpyxl`).
- **Auditable LLM Extraction (`backend/agent.py`):** Uses Google Gemini (`gemini-flash-latest`) to output structured line items along with field-level confidence scores ($0-100\%$) and exact source quote snippets.
- **5-Layer Guardrail Suite (`backend/guardrails.py`):**
  1. `balance_sheet_balances`: Mathematical check confirming $\text{Assets} \approx \text{Liabilities} + \text{Equity}$ (2% tolerance).
  2. `ebitda_exceeds_revenue`: Ensures $\text{EBITDA} \le \text{Total Revenue}$.
  3. `unit_currency_anomaly`: Detects $\sim 1000\times$ unit mismatches (e.g. ₹Crore vs ₹Lakh scaling errors).
  4. `source_snippet_unmatched`: Verifies extracted numbers exist literally within cited quote snippets.
  5. `extraction_incomplete` / `low_confidence_extraction`: Flags missing values ($0\%$ confidence) or fields extracted with $<50\%$ confidence.
- **Modern Audit Dashboard (`frontend/`):** React app featuring drag-and-drop file upload, top-level risk confidence badges (`High Risk / Audit Required`, `Medium Confidence`, `High Confidence`), formatted financial tables, and red-highlighted row alerts.

---

## 🛠️ Project Structure

```text
fin-extract-agent/
├── backend/
│   ├── agent.py          # Gemini API wrapper with JSON extraction prompt
│   ├── app.py            # Flask API (POST /api/analyze, GET /api/health)
│   ├── extractor.py      # PDF & Excel document text/table parser
│   ├── guardrails.py     # 5-layer mathematical and sanity audit checks
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── index.html        # HTML shell with Google Fonts
│   ├── package.json      # Vite + React dependencies
│   └── src/
│       ├── App.jsx       # Main React dashboard & risk badge logic
│       ├── index.css     # CSS design system (Dark slate theme)
│       └── main.jsx      # React entry point
├── FINDINGS.md           # Stress testing log, failure modes & roadmap
└── README.md             # Project documentation
```

---

## 🚀 Getting Started

### 1. Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # Add your GEMINI_API_KEY (from https://aistudio.google.com/apikey)
python app.py                # Runs on http://127.0.0.1:5000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev                  # Runs on http://localhost:5173
```

---

## 🛡️ Guardrail Rules Summary

| Guardrail Name | Severity | Condition & Action |
| :--- | :--- | :--- |
| **Balance Sheet Balance** | `HIGH` | Flags when $\text{Assets} \ne \text{Liabilities} + \text{Equity}$ ($>2\%$ deviation). |
| **EBITDA Sanity** | `HIGH` | Flags when $\text{EBITDA} > \text{Total Revenue}$. |
| **Unit Scaling Anomaly** | `HIGH` | Flags revenue/expense ratios off by $\sim 500\times - 5000\times$ (Crore vs Lakh). |
| **Extraction Completeness** | `HIGH` | Flags when $\ge 50\%$ of requested financial line items return `null`. |
| **Source Citation Check** | `MEDIUM` | Flags when extracted number is missing from source quote snippet. |
| **Low Confidence** | `MEDIUM`/`HIGH` | Flags fields extracted with $<50\%$ confidence or missing values. |

---

## 📄 Tested Scenarios & Documented Limitations (`FINDINGS.md`)

* **Clean Excel Extracts:** Parsed cleanly with $100\%$ confidence and zero flags.
* **Intentionally Broken Balance Sheet:** Caught asset mismatch ($795,000 \ne 350,000 + 520,000$), flagged `[HIGH]` balance sheet alert, and highlighted affected rows red.
* **Unextracted / Scanned PDFs:** `extraction_incomplete` guardrail immediately caught unread text layers, changing badge to `High Risk / Discrepancy Flagged` (Red).
* **Documented Limitations (Production Roadmap):**
  - *Scanned PDFs:* Requires OCR engine (`pytesseract` + `pdf2image`).
  - *Large Annual Reports ($>60\text{k}$ chars):* Needs section chunking and recency-weighted merging.
  - *Complex Merged Tables:* Requires `Camelot`/`Tabula` or vision-capable LLM parsing.
