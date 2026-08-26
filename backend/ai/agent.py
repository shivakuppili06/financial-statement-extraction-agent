"""
agent.py
Sends extracted text to Gemini and asks for a STRICT JSON schema
of financial line items. Uses RAG vector indexing for large documents
and emits telemetry to Azure Application Insights.
"""

import os
import json
import uuid
import google.generativeai as genai
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai.rag_store import rag_store
from observability.telemetry import app_logger
from resilience.circuit_breaker import gemini_circuit_breaker, CircuitBreakerOpenException
from resilience.rate_limiter import call_with_retry_and_rate_limit
from observability.metrics import metrics_tracker

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

MODEL_NAME = "gemini-flash-latest"

EXTRACTION_PROMPT = """You are a financial analyst assistant. You will be given
raw, messy text extracted from a company's financial statement (PDF or Excel).

Extract the following line items if present, for the most recent reporting
period found in the document:
- total_revenue
- total_expenses
- ebitda
- net_income
- total_assets
- total_liabilities
- total_equity

Return ONLY valid JSON, no markdown fences, no commentary, in this exact shape:

{
  "period_label": "<e.g. FY2024 or Q3 2025>",
  "line_items": {
    "total_revenue": {"value": <number or null>, "confidence": <0-1>, "source_snippet": "<short quote from the text>"},
    "total_expenses": {"value": <number or null>, "confidence": <0-1>, "source_snippet": "..."},
    "ebitda": {"value": <number or null>, "confidence": <0-1>, "source_snippet": "..."},
    "net_income": {"value": <number or null>, "confidence": <0-1>, "source_snippet": "..."},
    "total_assets": {"value": <number or null>, "confidence": <0-1>, "source_snippet": "..."},
    "total_liabilities": {"value": <number or null>, "confidence": <0-1>, "source_snippet": "..."},
    "total_equity": {"value": <number or null>, "confidence": <0-1>, "source_snippet": "..."}
  }
}

If a value cannot be found, set "value" to null and "confidence" to 0.

RAW DOCUMENT TEXT:
---
{document_text}
---
"""


def extract_financials_fallback(document_text: str) -> dict:
    """
    Rule-based regex fallback extractor used when Gemini API is unreachable or key is unconfigured.
    """
    import re
    app_logger.warning("Using rule-based regex fallback extractor for financial statement.")
    
    def find_number(patterns, text):
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val_str = match.group(1).replace(",", "").strip()
                try:
                    return float(val_str), match.group(0)
                except ValueError:
                    pass
        return None, None

    rev_val, rev_src = find_number([r"total\s+revenue[^\d]*([\d,]+(?:\.\d+)?)", r"revenue[^\d]*([\d,]+(?:\.\d+)?)"], document_text)
    exp_val, exp_src = find_number([r"total\s+expenses[^\d]*([\d,]+(?:\.\d+)?)", r"expenses[^\d]*([\d,]+(?:\.\d+)?)"], document_text)
    ebitda_val, ebitda_src = find_number([r"ebitda[^\d]*([\d,]+(?:\.\d+)?)"], document_text)
    net_val, net_src = find_number([r"net\s+income[^\d]*([\d,]+(?:\.\d+)?)"], document_text)
    asset_val, asset_src = find_number([r"total\s+assets[^\d]*([\d,]+(?:\.\d+)?)", r"assets[^\d]*([\d,]+(?:\.\d+)?)"], document_text)
    liab_val, liab_src = find_number([r"total\s+liabilities[^\d]*([\d,]+(?:\.\d+)?)", r"liabilities[^\d]*([\d,]+(?:\.\d+)?)"], document_text)
    eq_val, eq_src = find_number([r"total\s+equity[^\d]*([\d,]+(?:\.\d+)?)", r"equity[^\d]*([\d,]+(?:\.\d+)?)"], document_text)

    # Period detection
    period_match = re.search(r"(FY\s*20\d\d|Q[1-4]\s*20\d\d|20\d\d)", document_text, re.IGNORECASE)
    period_label = period_match.group(1) if period_match else "FY2024"

    return {
        "period_label": f"{period_label} (Regex Fallback)",
        "line_items": {
            "total_revenue": {"value": rev_val, "confidence": 0.85 if rev_val else 0.0, "source_snippet": rev_src or "N/A"},
            "total_expenses": {"value": exp_val, "confidence": 0.85 if exp_val else 0.0, "source_snippet": exp_src or "N/A"},
            "ebitda": {"value": ebitda_val, "confidence": 0.85 if ebitda_val else 0.0, "source_snippet": ebitda_src or "N/A"},
            "net_income": {"value": net_val, "confidence": 0.85 if net_val else 0.0, "source_snippet": net_src or "N/A"},
            "total_assets": {"value": asset_val, "confidence": 0.85 if asset_val else 0.0, "source_snippet": asset_src or "N/A"},
            "total_liabilities": {"value": liab_val, "confidence": 0.85 if liab_val else 0.0, "source_snippet": liab_src or "N/A"},
            "total_equity": {"value": eq_val, "confidence": 0.85 if eq_val else 0.0, "source_snippet": eq_src or "N/A"},
        }
    }


def extract_financials(document_text: str) -> dict:
    doc_id = str(uuid.uuid4())[:8]
    app_logger.info(f"Processing document extraction (ID: {doc_id}) with length {len(document_text)} characters.")

    # Check Circuit Breaker before making call
    try:
        gemini_circuit_breaker.check_allow_request()
    except CircuitBreakerOpenException as e:
        app_logger.warning(f"Circuit breaker active for doc {doc_id}. Using rule-based fallback.")
        return extract_financials_fallback(document_text)

    # RAG Vector indexing step for large reports (>30k characters)
    if len(document_text) > 30000:
        app_logger.info(f"Document {doc_id} exceeds 30k chars. Indexing in RAG vector store.")
        rag_store.index_document(doc_id, document_text)
        query = "revenue expenses ebitda net income assets liabilities equity balance sheet income statement"
        context_text = rag_store.retrieve_relevant_context(query, document_text, top_k=6)
    else:
        context_text = document_text[:60000]

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key or not api_key.startswith("AIzaSy"):
        app_logger.warning(f"GEMINI_API_KEY is not configured or invalid for doc {doc_id}. Falling back to rule-based parser.")
        return extract_financials_fallback(document_text)

    model = genai.GenerativeModel(MODEL_NAME)
    prompt = EXTRACTION_PROMPT.replace("{document_text}", context_text)

    try:
        response = call_with_retry_and_rate_limit(model.generate_content, prompt, request_options={"timeout": 10.0})
        gemini_circuit_breaker.record_success()
        metrics_tracker.record_gemini_call(success=True)
    except Exception as e:
        gemini_circuit_breaker.record_failure()
        metrics_tracker.record_gemini_call(success=False)
        app_logger.error(f"Gemini API call failed for doc {doc_id}: {e}. Falling back to rule-based parser.")
        return extract_financials_fallback(document_text)

    raw = response.text.strip()

    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json\n", "", 1)

    try:
        data = json.loads(raw)
        app_logger.info(f"Extraction successful for doc {doc_id}. Period label: {data.get('period_label')}")
        return data
    except json.JSONDecodeError as e:
        app_logger.error(f"Extraction failed for doc {doc_id}. Invalid JSON from LLM: {e}")
        return extract_financials_fallback(document_text)


