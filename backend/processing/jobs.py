"""
jobs.py
Async job runner and task definition for document extraction.
Supports RQ (Redis Queue) with a fallback threaded queue runner.
"""

import os
import time
import json
import uuid
import tempfile
import threading
import sys
import requests
import redis

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from processing.extractor import extract_raw_content
from ai.agent import extract_financials
from processing.guardrails import run_all_checks
from resilience.idempotency import idempotency_manager
from observability.metrics import metrics_tracker
from observability.telemetry import app_logger
from resilience.redis_client import get_redis_client

# In-memory store fallback for job status
_job_store = {}
_job_store_lock = threading.Lock()

def get_redis_connection():
    return get_redis_client()

def update_job_status(job_id: str, status: str, result: dict = None, error: str = None, latency: float = None):
    r = get_redis_connection()
    data = {
        "job_id": job_id,
        "status": status,
        "result": result,
        "error": error,
        "latency_seconds": latency,
        "updated_at": time.time()
    }
    if r:
        try:
            r.setex(f"job:{job_id}", 86400, json.dumps(data))
            return
        except Exception:
            pass

    with _job_store_lock:
        _job_store[job_id] = data

def get_job_status(job_id: str) -> dict:
    r = get_redis_connection()
    if r:
        try:
            val = r.get(f"job:{job_id}")
            if val:
                return json.loads(val.decode('utf-8'))
        except Exception:
            pass

    with _job_store_lock:
        return _job_store.get(job_id)

def process_document_job(job_id: str, file_bytes: bytes, filename: str, webhook_url: str = None):
    """
    Background worker function executing the full extraction pipeline.
    """
    start_time = time.time()
    update_job_status(job_id, status="processing")
    app_logger.info(f"Starting async processing for job {job_id} ({filename})")

    ext = os.path.splitext(filename)[1].lower()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        # Check SHA-256 Idempotency cache first
        file_hash = idempotency_manager.compute_hash(file_bytes)
        cached = idempotency_manager.get_cached_result(file_hash)
        if cached:
            app_logger.info(f"Job {job_id}: Hit SHA-256 idempotency cache for {file_hash[:10]}")
            elapsed = time.time() - start_time
            update_job_status(job_id, status="completed", result=cached, latency=elapsed)
            metrics_tracker.record_job_completed(elapsed)
            _send_webhook_if_configured(webhook_url, job_id, "completed", cached)
            return cached

        raw_text = extract_raw_content(tmp_path)
        if not raw_text.strip():
            raise ValueError("No extractable text found in document.")

        extraction = extract_financials(raw_text)
        flags = run_all_checks(extraction)

        final_payload = {
            "extraction": extraction,
            "flags": flags,
            "file_hash": file_hash
        }

        # Cache result for future duplicate uploads
        idempotency_manager.cache_result(file_hash, final_payload)

        elapsed = round(time.time() - start_time, 4)
        update_job_status(job_id, status="completed", result=final_payload, latency=elapsed)
        metrics_tracker.record_job_completed(elapsed)
        app_logger.info(f"Job {job_id} completed successfully in {elapsed}s.")

        _send_webhook_if_configured(webhook_url, job_id, "completed", final_payload)
        return final_payload

    except Exception as e:
        elapsed = round(time.time() - start_time, 4)
        err_msg = str(e)
        app_logger.error(f"Job {job_id} failed after {elapsed}s: {err_msg}")
        update_job_status(job_id, status="failed", error=err_msg, latency=elapsed)
        metrics_tracker.record_job_failed()
        _send_webhook_if_configured(webhook_url, job_id, "failed", {"error": err_msg})
        raise e
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def _send_webhook_if_configured(webhook_url: str, job_id: str, status: str, payload: dict):
    if not webhook_url:
        return
    try:
        requests.post(webhook_url, json={"job_id": job_id, "status": status, "payload": payload}, timeout=5)
        app_logger.info(f"Webhook notification sent to {webhook_url} for job {job_id}")
    except Exception as e:
        app_logger.warning(f"Failed to post webhook to {webhook_url} for job {job_id}: {e}")

def enqueue_job(file_bytes: bytes, filename: str, webhook_url: str = None) -> str:
    """
    Submits a document job to RQ or background thread worker.
    """
    job_id = str(uuid.uuid4())
    metrics_tracker.record_job_queued()
    update_job_status(job_id, status="queued")

    r = get_redis_connection()
    if r:
        try:
            from rq import Queue
            q = Queue(connection=r)
            q.enqueue(process_document_job, job_id, file_bytes, filename, webhook_url, job_id=job_id)
            app_logger.info(f"Enqueued job {job_id} to RQ worker queue.")
            return job_id
        except Exception as e:
            app_logger.warning(f"Failed to enqueue to RQ ({e}), using thread pool fallback.")

    # Thread pool fallback if Redis / RQ is offline
    t = threading.Thread(target=process_document_job, args=(job_id, file_bytes, filename, webhook_url))
    t.daemon = True
    t.start()
    app_logger.info(f"Enqueued job {job_id} to background thread.")
    return job_id
