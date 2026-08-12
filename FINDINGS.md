# Financial Statement Extraction Agent — Stress Test & Audit Findings

## Document Testing Log & Findings

### Test 1: Synthetic/Simple Financial Workbook (`Financial_Statement.xlsx`)
* **Extraction Result:** Clean extraction across all 7 line items (`total_revenue`, `total_expenses`, `ebitda`, `net_income`, `total_assets`, `total_liabilities`, `total_equity`).
* **Confidence Scores:** 100% across all fields.
* **Guardrails Triggered:** None (Clean Pass).

---

### Test 2: Inconsistent Balance Sheet (`broken_financial_statement.xlsx`)
* **Simulated Error:** Shifted `total_liabilities` to 350,000 while keeping `total_assets` = 795,000 and `total_equity` = 520,000 ($795,000 \ne 350,000 + 520,000$).
* **Guardrails Triggered:**
  - `[high] balance_sheet_balances`: Assets (795,000) does not equal Liabilities + Equity (870,000). Off by 8.6%.
* **UI Behavior:** Displayed top-level **"High Risk / Discrepancy Flagged"** Red Badge and highlighted balance sheet line item rows red in data table.

---

### Key Technical Limitations & Required Upgrades (Production Roadmap)

1. **Scanned Image PDFs (Lack of Text Layer)**
   - **Current Behavior:** `pdfplumber` yields empty string, resulting in 422 API response.
   - **Root Cause:** Standard text extractor cannot parse image raster data.
   - **Recommended Fix:** Integrate `pytesseract` / `pdf2image` OCR fallback pipeline when `pdfplumber` returns empty text.

2. **Large Annual Report Truncation**
   - **Current Behavior:** Text is hard truncated at 60,000 characters in `agent.py`.
   - **Root Cause:** Single LLM prompt context window limits.
   - **Recommended Fix:** Implement page/section document chunking, extract per section, and merge line items with recency/relevance resolution.

3. **Complex Multi-Header Table Merges**
   - **Current Behavior:** Table text flattening can misalign columns across multiple years.
   - **Recommended Fix:** Upgrade table parsing using `Camelot` / `Tabula` or feed raw page images to vision-capable multimodal models.
