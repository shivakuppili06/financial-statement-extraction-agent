"""
app.py
Flask API: upload a financial document -> async job processing, idempotency caching,
rate limiting, circuit breaking, and metrics endpoint.

Endpoints:
  POST /api/analyze or /api/jobs  (multipart/form-data, field name "file", optional "webhook_url")
      -> { job_id: "...", status: "queued|completed", cached: true|false }
  GET  /api/jobs/<job_id>
      -> { job_id: "...", status: "queued|processing|completed|failed", result: {...}, error: "..." }
  GET  /metrics
      -> { jobs_processed: ..., jobs_in_queue: ..., average_extraction_latency_seconds: ..., gemini_api_error_rate: ..., cache_hit_rate: ... }

Run:
  pip install -r requirements.txt
  cp .env.example .env   # add your GEMINI_API_KEY
  python app.py
"""

import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from resilience.idempotency import idempotency_manager
from processing.jobs import enqueue_job, get_job_status
from observability.metrics import metrics_tracker

app = Flask(__name__)
CORS(app)

ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xlsm"}


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/metrics", methods=["GET"])
@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    summary = metrics_tracker.get_metrics_summary()
    return jsonify(summary)


@app.route("/api/analyze", methods=["GET", "POST"])
@app.route("/api/jobs", methods=["GET", "POST"])
def submit_job():
    if request.method == "GET":
        return jsonify({
            "message": "Financial Statement Extraction Job API",
            "usage": {
                "submit_document": "POST /api/jobs or /api/analyze with multipart/form-data field 'file'",
                "poll_job_status": "GET /api/jobs/<job_id>",
                "observability_metrics": "GET /metrics"
            }
        }), 200

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    filename = file.filename or "document.pdf"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Unsupported file type: {ext}"}), 400

    webhook_url = request.form.get("webhook_url") or request.args.get("webhook_url")
    is_sync = request.args.get("sync", "").lower() == "true" or request.form.get("sync", "").lower() == "true"

    file_bytes = file.read()
    if not file_bytes:
        return jsonify({"error": "Uploaded file is empty"}), 400

    # 1. Idempotency Check (SHA-256)
    file_hash = idempotency_manager.compute_hash(file_bytes)
    cached_result = idempotency_manager.get_cached_result(file_hash)
    if cached_result:
        return jsonify({
            "job_id": f"cached-{file_hash[:8]}",
            "status": "completed",
            "cached": True,
            "file_hash": file_hash,
            "extraction": cached_result.get("extraction"),
            "flags": cached_result.get("flags")
        }), 200

    # 2. Async Queue Submission
    job_id = enqueue_job(file_bytes=file_bytes, filename=filename, webhook_url=webhook_url)

    if is_sync:
        # If client explicitly asked for synchronous processing (for backward compatibility)
        import time
        start = time.time()
        while time.time() - start < 60:
            status_info = get_job_status(job_id)
            if status_info and status_info.get("status") in ("completed", "failed"):
                if status_info["status"] == "completed":
                    res = status_info.get("result", {})
                    return jsonify({
                        "extraction": res.get("extraction"),
                        "flags": res.get("flags"),
                        "job_id": job_id
                    }), 200
                else:
                    return jsonify({"error": status_info.get("error")}), 502
            time.sleep(0.5)
        return jsonify({"error": "Sync processing timeout", "job_id": job_id}), 504

    return jsonify({
        "job_id": job_id,
        "status": "queued",
        "cached": False,
        "poll_url": f"/api/jobs/{job_id}"
    }), 202


@app.route("/api/jobs/<job_id>", methods=["GET"])
def poll_job(job_id: str):
    job_info = get_job_status(job_id)
    if not job_info:
        return jsonify({"error": f"Job ID {job_id} not found"}), 404
    return jsonify(job_info), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
