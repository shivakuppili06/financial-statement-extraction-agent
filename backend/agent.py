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
from dotenv import load_dotenv
from rag_store import rag_store
from telemetry import app_logger

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


def extract_financials(document_text: str) -> dict:
    doc_id = str(uuid.uuid4())[:8]
    app_logger.info(f"Processing document extraction (ID: {doc_id}) with length {len(document_text)} characters.")

    # RAG Vector indexing step for large reports (>30k characters)
    if len(document_text) > 30000:
        app_logger.info(f"Document {doc_id} exceeds 30k chars. Indexing in RAG vector store.")
        rag_store.index_document(doc_id, document_text)
        query = "revenue expenses ebitda net income assets liabilities equity balance sheet income statement"
        context_text = rag_store.retrieve_relevant_context(query, document_text, top_k=6)
    else:
        context_text = document_text[:60000]

    model = genai.GenerativeModel(MODEL_NAME)
    prompt = EXTRACTION_PROMPT.replace("{document_text}", context_text)

    response = model.generate_content(prompt)
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
        raise ValueError(f"Model did not return valid JSON: {e}\nRaw output:\n{raw}")
