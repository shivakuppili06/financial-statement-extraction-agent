"""
app.py
Flask API: upload a financial document -> get structured extraction + flags.

Endpoints:
  POST /api/analyze   (multipart/form-data, field name "file")
      -> { extraction: {...}, flags: [...] }

Run:
  pip install -r requirements.txt
  cp .env.example .env   # add your GEMINI_API_KEY
  python app.py
"""

import os
import tempfile

from flask import Flask, request, jsonify
from flask_cors import CORS

from extractor import extract_raw_content
from agent import extract_financials
from guardrails import run_all_checks

app = Flask(__name__)
CORS(app)

ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xlsm"}


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Unsupported file type: {ext}"}), 400

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        raw_text = extract_raw_content(tmp_path)
        if not raw_text.strip():
            return jsonify({"error": "No extractable text found (scanned/image PDF?)"}), 422

        extraction = extract_financials(raw_text)
        flags = run_all_checks(extraction)

        return jsonify({"extraction": extraction, "flags": flags})

    except ValueError as e:
        return jsonify({"error": str(e)}), 502
    finally:
        os.remove(tmp_path)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
