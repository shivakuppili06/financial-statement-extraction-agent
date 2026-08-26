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
- **⚡ .NET Core (`dotnet-backend/`):** Enterprise API gateway, authentication, data persistence, and orchestration layer (.NET 8 Web API).
- **🐍 Python (`backend/`):** AI / LLM extraction microservice using Google Gemini (`gemini-flash-latest`), document parsing (`pdfplumber`, `openpyxl`), and 5-layer mathematical guardrail suite.
- **🔄 Async Queue & Resiliency:** Redis Queue (RQ) background job queue, SHA-256 idempotency cache, Gemini API sliding-window rate limiter with 429 backoff retries, circuit breaker state machine, and JSON observability metrics.
- **⚛️ React (`frontend/`):** Interactive web dashboard (Vite + React) for visual statement inspection, risk scoring badges, and mathematical audit table highlighting.
- **📱 Ionic (`mobile/`):** Cross-platform mobile audit application (Ionic + React + Capacitor) for mobile financial field audits and document capturing.
- **🔍 Vector DB & RAG Strategy:** **Azure AI Search** & **ChromaDB** vector stores indexing chunked 10-K/10-Q financial reports for similarity search and recency-weighted retrieval.
- **☁️ Azure Cloud Infrastructure:** Hosted on **Azure Container Apps** with **Azure Blob Storage** for raw statement PDF/Excel document archives and secret management via **Azure Key Vault**.
- **📊 Logging & Observability:** Telemetry, distributed request tracing, and guardrail audit logging via **Azure Application Insights**, **OpenTelemetry**, and custom `/metrics` JSON endpoint.

---

## 🌟 Key Features

- **Document Processing Pipeline:** Extracts raw text & table grids from PDF balance sheets/P&L extracts (`pdfplumber`) and multi-sheet Excel files (`openpyxl`).
- **Auditable LLM Extraction (`backend/agent.py`):** Uses Google Gemini (`gemini-flash-latest`) to output structured line items along with field-level confidence scores ($0-100\%$) and exact source quote snippets.
- **Async Job Queue (`backend/jobs.py`):** Moves PDF extraction off HTTP request threads into an asynchronous Redis Queue (RQ) worker with status polling (`GET /api/jobs/<job_id>`) and webhook callback notifications.
- **SHA-256 Idempotency (`backend/idempotency.py`):** Hashes uploaded documents to cache extraction results, returning cached responses in <10ms for duplicate uploads without invoking Gemini API calls.
- **Gemini API Rate Limiting & Backoff (`backend/rate_limiter.py`):** Redis-backed sliding window rate limiter with automated exponential backoff on HTTP 429 / `ResourceExhausted` quota limits.
- **Circuit Breaker Resiliency (`backend/circuit_breaker.py`):** Implements a 3-state machine (`CLOSED`, `OPEN`, `HALF_OPEN`) that trips on 5 consecutive failures in 60s, fast-failing during cooldown periods to prevent downstream failure cascades.
- **Observability Metrics Endpoint (`/metrics`):** Exposes real-time operational statistics (`jobs_processed`, `jobs_in_queue`, `average_extraction_latency_seconds`, `gemini_api_error_rate`, `cache_hit_rate`).
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
│
├── backend/                    # Python AI & processing service
│   ├── api/                   # REST API
│   │   └── app.py
│   ├── ai/                    # LLM & RAG
│   │   ├── agent.py
│   │   └── rag_store.py
│   ├── processing/            # Document extraction & validation
│   │   ├── extractor.py
│   │   ├── guardrails.py
│   │   └── jobs.py
│   ├── resilience/            # Reliability & fault tolerance
│   │   ├── circuit_breaker.py
│   │   ├── rate_limiter.py
│   │   ├── idempotency.py
│   │   └── redis_client.py
│   ├── observability/         # Metrics & telemetry
│   │   ├── metrics.py
│   │   └── telemetry.py
│   ├── worker.py              # Background worker
│   ├── test_system.py         # Backend system tests
│   └── requirements.txt
│
├── dotnet-backend/             # .NET 8 Enterprise API Gateway
│   ├── Controllers/
│   ├── Models/
│   ├── Program.cs
│   └── dotnet-backend.csproj
│
├── frontend/                   # React + Vite Web Dashboard
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── mobile/                     # Ionic + Capacitor Mobile App
│   ├── src/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── ionic.config.json
│
├── tests/                      # Integration & upload tests
│   └── test_upload.py
│
├── samples/                    # Sample financial documents
│   └── broken_financial_statement.xlsx
│
├── docs/                       # Project documentation
│   └── FINDINGS.md
│
├── README.md
└── LICENSE
```

---

## 🚀 Getting Started

### 1. Python Backend & Async Worker Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # Add your GEMINI_API_KEY (from https://aistudio.google.com/apikey)

# Start Flask API server (http://127.0.0.1:5000)
python api/app.py

# Optional: Run RQ background queue worker (if Redis is running)
python worker.py
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