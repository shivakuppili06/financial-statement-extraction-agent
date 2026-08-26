"""
test_system.py
Automated test suite verifying Async Queue, Gemini Rate Limiter,
Circuit Breaker, Idempotency Caching, and Metrics Observability.
"""

import sys
import os
import io
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from api.app import app
from resilience.idempotency import idempotency_manager, IdempotencyManager
from resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from resilience.rate_limiter import GeminiRateLimiter, RateLimitExceededException, call_with_retry_and_rate_limit
from observability.metrics import MetricsTracker, metrics_tracker
from processing.jobs import process_document_job, enqueue_job, get_job_status


class TestIdempotency(unittest.TestCase):
    def test_sha256_hashing_and_cache(self):
        mgr = IdempotencyManager()
        sample_bytes = b"PDF Content Sample Data 123"
        file_hash = mgr.compute_hash(sample_bytes)
        
        self.assertEqual(len(file_hash), 64)
        self.assertIsNone(mgr.get_cached_result(file_hash))

        payload = {"extraction": {"total_revenue": 1000}, "flags": []}
        mgr.cache_result(file_hash, payload)

        cached = mgr.get_cached_result(file_hash)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["extraction"]["total_revenue"], 1000)


class TestCircuitBreaker(unittest.TestCase):
    def test_circuit_breaker_tripping_and_cooldown(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0, window_seconds=10.0)
        self.assertTrue(cb.check_allow_request())

        cb.record_failure()
        cb.record_failure()
        self.assertTrue(cb.check_allow_request())

        # 3rd failure trips circuit breaker
        cb.record_failure()
        with self.assertRaises(CircuitBreakerOpenException):
            cb.check_allow_request()

        # Wait for recovery cooldown timeout
        time.sleep(1.1)
        # Allows request in HALF_OPEN state
        self.assertTrue(cb.check_allow_request())

        # Success resets to CLOSED
        cb.record_success()
        self.assertTrue(cb.check_allow_request())


class TestRateLimiter(unittest.TestCase):
    def test_rate_limiter_exponential_backoff(self):
        limiter = GeminiRateLimiter(max_requests=2, window_seconds=10.0)
        self.assertTrue(limiter.acquire())
        self.assertTrue(limiter.acquire())

        # 3rd request inside window times out
        with self.assertRaises(RateLimitExceededException):
            limiter.acquire(timeout=0.2)

        # Retry with exponential backoff on 429 error
        mock_func = MagicMock()
        mock_func.side_effect = [ValueError("429 ResourceExhausted rate limit"), "success"]

        result = call_with_retry_and_rate_limit(mock_func, max_retries=2, initial_delay=0.1)
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 2)


class TestMetricsTracker(unittest.TestCase):
    def test_metrics_counters_and_ratios(self):
        tracker = MetricsTracker()
        tracker.record_job_queued()
        tracker.record_job_completed(latency_seconds=2.5)
        tracker.record_gemini_call(success=True)
        tracker.record_gemini_call(success=False)
        tracker.record_cache_check(hit=True)
        tracker.record_cache_check(hit=False)

        summary = tracker.get_metrics_summary()
        self.assertEqual(summary["jobs_processed"], 1)
        self.assertEqual(summary["jobs_in_queue"], 0)
        self.assertEqual(summary["average_extraction_latency_seconds"], 2.5)
        self.assertEqual(summary["gemini_api_error_rate"], 0.5)
        self.assertEqual(summary["cache_hit_rate"], 0.5)


class TestFlaskEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})

    def test_metrics_endpoint(self):
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        self.assertIn("jobs_processed", response.json)
        self.assertIn("gemini_api_error_rate", response.json)
        self.assertIn("cache_hit_rate", response.json)

    @patch("api.app.enqueue_job")
    @patch("api.app.get_job_status")
    def test_job_submission_and_polling(self, mock_get_status, mock_enqueue):
        mock_enqueue.return_value = "mock-job-123"
        mock_get_status.return_value = {"job_id": "mock-job-123", "status": "queued"}

        # Submit document
        data = {
            "file": (io.BytesIO(b"%PDF-1.4 Mock PDF Content"), "test_statement.pdf")
        }
        res = self.client.post("/api/jobs", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 202)
        job_id = res.json["job_id"]
        self.assertEqual(job_id, "mock-job-123")
        self.assertEqual(res.json["status"], "queued")

        # Poll job status
        poll_res = self.client.get(f"/api/jobs/{job_id}")
        self.assertEqual(poll_res.status_code, 200)
        self.assertEqual(poll_res.json["status"], "queued")



if __name__ == "__main__":
    import sys
    res = unittest.main(exit=False)
    sys.exit(0 if res.result.wasSuccessful() else 1)


