"""
agent.py
Sends the raw extracted text to Gemini and asks for a STRICT JSON schema
of financial line items. This is the core "AI agent" of the project.

Design note: we ask the model to also return a `confidence` per field and
a `source_snippet` it based the number on — this is what makes the output
auditable instead of a black box. A banker needs to know WHERE a number
came from, not just what it is.
"""

import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

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
    # Gemini has a context window but not an infinite one — truncate
    # defensively for very large annual reports. TODO: chunk + merge
    # instead of truncating (see README).
    truncated = document_text[:60000]

    model = genai.GenerativeModel(MODEL_NAME)
    prompt = EXTRACTION_PROMPT.replace("{document_text}", truncated)

    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Models sometimes wrap JSON in ```json fences despite instructions.
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json\n", "", 1)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        # Don't silently fail — surface the raw model output so you can
        # debug prompt issues. This IS the kind of failure mode worth
        # writing up in your README.
        raise ValueError(f"Model did not return valid JSON: {e}\nRaw output:\n{raw}")
