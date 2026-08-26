# Financial Statement Extraction & Sanity-Check Agent

[![.NET Core](https://img.shields.io/badge/.NET%20Core-8.0-512BD4?style=flat&logo=.net&logoColor=white)](https://dotnet.microsoft.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Ionic](https://img.shields.io/badge/Ionic-7.0+-3880FF?style=flat&logo=ionic&logoColor=white)](https://ionicframework.com/)
[![React](https://img.shields.io/badge/React-18.0+-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Azure](https://img.shields.io/badge/Azure-Cloud-0089D6?style=flat&logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/)
[![Vector DB](https://img.shields.io/badge/Vector%20DB-Azure%20AI%20Search-0078D4?style=flat&logo=microsoft&logoColor=white)](https://azure.microsoft.com/en-us/products/ai-services/ai-search)
[![Monitoring](https://img.shields.io/badge/Monitoring-App%20Insights-0078D4?style=flat&logo=microsoft&logoColor=white)](https://learn.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview)

An enterprise autonomous LLM financial analysis suite built with **.NET Core** (Web API Gateway), **Python** (Gemini AI Extraction & Guardrail Microservice), **React** (Web Audit Dashboard), and **Ionic** (Cross-Platform Mobile App), backed by **Azure Cloud Services**, **Azure AI Search (Vector DB / RAG)**, and **Azure Application Insights**.

---

## 💻 Tech Stack & Ecosystem Architecture

- **⚡ .NET Core (`dotnet-backend/`):** Enterprise API gateway, authentication, data persistence, and orchestration layer (.NET 8 Web API).
- **🐍 Python (`backend/`):** AI / LLM extraction service using Google Gemini (`gemini-flash-latest`), document parsing (`pdfplumber`, `openpyxl`), and 5-layer mathematical guardrail suite.
- **⚛️ React (`frontend/`):** Interactive web dashboard (Vite + React) for visual statement inspection, risk scoring badges, and mathematical audit table highlighting.
- **📱 Ionic (`mobile/`):** Cross-platform mobile audit application (Ionic + React + Capacitor) for mobile financial field audits and document capturing.
- **🔍 Vector DB & RAG Strategy:** **Azure AI Search** & **ChromaDB** vector stores indexing chunked 10-K/10-Q financial reports for similarity search and recency-weighted retrieval.
- **☁️ Azure Cloud Infrastructure:** Hosted on **Azure Container Apps** with **Azure Blob Storage** for raw statement PDF/Excel document archives and secret management via **Azure Key Vault**.
- **📊 Logging & Observability:** Telemetry, distributed request tracing, and guardrail audit logging via **Azure Application Insights** and **OpenTelemetry**.

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
- **Mobile Audit App (`mobile/`):** Ionic React cross-platform app for mobile audits and document upload.

---

## 🛠️ Project Structure

```text
fin-extract-agent/
├── backend/                  # Python AI & Guardrail Microservice
│   ├── agent.py              # Gemini API wrapper with JSON extraction prompt
│   ├── app.py                # Flask API (POST /api/analyze, GET /api/health)
│   ├── extractor.py          # PDF & Excel document text/table parser
│   ├── guardrails.py         # 5-layer mathematical and sanity audit checks
│   └── requirements.txt      # Python dependencies
├── dotnet-backend/           # .NET Core Enterprise Gateway & API
│   ├── Controllers/          # API Controllers
│   ├── Models/               # Data Transfer Objects & Domain Models
│   ├── Program.cs            # .NET 8 Web API entry point
│   └── dotnet-backend.csproj # .NET Core project file
├── frontend/                 # React Web Audit Dashboard
│   ├── index.html            # HTML shell with Google Fonts
│   ├── package.json          # Vite + React dependencies
│   └── src/
│       ├── App.jsx           # Main React dashboard & risk badge logic
│       ├── index.css         # CSS design system (Dark slate theme)
│       └── main.jsx          # React entry point
├── mobile/                   # Ionic Cross-Platform Mobile App
│   ├── package.json          # Ionic + React dependencies
│   └── src/
│       ├── App.tsx           # Ionic React entry point & UI shell
│       └── main.tsx          # App initialization
├── FINDINGS.md               # Stress testing log, failure modes & roadmap
└── README.md                 # Project documentation
```

---

## 🚀 Getting Started

### 1. Python Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # Add your GEMINI_API_KEY (from https://aistudio.google.com/apikey)
python app.py                # Runs on http://127.0.0.1:5000
```

### 2. .NET Core Web API Setup
```bash
cd dotnet-backend
dotnet run                   # Runs on http://localhost:5200
```

### 3. React Frontend Setup
```bash
cd frontend
npm install
npm run dev                  # Runs on http://localhost:5173
```

### 4. Ionic Mobile Setup
```bash
cd mobile
npm install
npm run dev                  # Runs on http://localhost:8100
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
  - *Large Annual Reports ($>60\text{k}$ chars):* Needs section chunking, vector indexing (Azure AI Search / ChromaDB), and recency-weighted merging.
  - *Complex Merged Tables:* Requires `Camelot`/`Tabula` or vision-capable LLM parsing.