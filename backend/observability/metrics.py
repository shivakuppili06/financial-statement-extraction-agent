"""
metrics.py
Observability metrics tracking module for Financial Statement Extraction Agent.
Backed by Redis with an in-memory fallback for local development.
"""

import time
import threading
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from resilience.redis_client import get_redis_client

class MetricsTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self.redis_client = get_redis_client()

        # In-memory fallbacks
        self._jobs_processed = 0
        self._jobs_queued = 0
        self._total_latency = 0.0
        self._gemini_calls = 0
        self._gemini_errors = 0
        self._cache_hits = 0
        self._cache_checks = 0

    def record_job_queued(self):
        if self.redis_client:
            try:
                self.redis_client.incr("metrics:jobs_queued")
                return
            except Exception:
                pass
        with self._lock:
            self._jobs_queued += 1

    def record_job_completed(self, latency_seconds: float):
        if self.redis_client:
            try:
                pipe = self.redis_client.pipeline()
                pipe.incr("metrics:jobs_processed")
                pipe.decr("metrics:jobs_queued")
                pipe.incrbyfloat("metrics:total_latency", latency_seconds)
                pipe.execute()
                return
            except Exception:
                pass
        with self._lock:
            self._jobs_processed += 1
            if self._jobs_queued > 0:
                self._jobs_queued -= 1
            self._total_latency += latency_seconds

    def record_job_failed(self):
        if self.redis_client:
            try:
                self.redis_client.decr("metrics:jobs_queued")
                return
            except Exception:
                pass
        with self._lock:
            if self._jobs_queued > 0:
                self._jobs_queued -= 1

    def record_gemini_call(self, success: bool):
        if self.redis_client:
            try:
                pipe = self.redis_client.pipeline()
                pipe.incr("metrics:gemini_calls")
                if not success:
                    pipe.incr("metrics:gemini_errors")
                pipe.execute()
                return
            except Exception:
                pass
        with self._lock:
            self._gemini_calls += 1
            if not success:
                self._gemini_errors += 1

    def record_cache_check(self, hit: bool):
        if self.redis_client:
            try:
                pipe = self.redis_client.pipeline()
                pipe.incr("metrics:cache_checks")
                if hit:
                    pipe.incr("metrics:cache_hits")
                pipe.execute()
                return
            except Exception:
                pass
        with self._lock:
            self._cache_checks += 1
            if hit:
                self._cache_hits += 1

    def get_metrics_summary(self) -> dict:
        if self.redis_client:
            try:
                pipe = self.redis_client.pipeline()
                pipe.get("metrics:jobs_processed")
                pipe.get("metrics:jobs_queued")
                pipe.get("metrics:total_latency")
                pipe.get("metrics:gemini_calls")
                pipe.get("metrics:gemini_errors")
                pipe.get("metrics:cache_hits")
                pipe.get("metrics:cache_checks")
                res = pipe.execute()

                jobs_processed = int(res[0] or 0)
                jobs_queued = max(0, int(res[1] or 0))
                total_latency = float(res[2] or 0.0)
                gemini_calls = int(res[3] or 0)
                gemini_errors = int(res[4] or 0)
                cache_hits = int(res[5] or 0)
                cache_checks = int(res[6] or 0)

                avg_latency = round(total_latency / jobs_processed, 4) if jobs_processed > 0 else 0.0
                gemini_error_rate = round(gemini_errors / gemini_calls, 4) if gemini_calls > 0 else 0.0
                cache_hit_rate = round(cache_hits / cache_checks, 4) if cache_checks > 0 else 0.0

                return {
                    "jobs_processed": jobs_processed,
                    "jobs_in_queue": jobs_queued,
                    "average_extraction_latency_seconds": avg_latency,
                    "gemini_api_error_rate": gemini_error_rate,
                    "cache_hit_rate": cache_hit_rate,
                    "raw_counters": {
                        "gemini_calls": gemini_calls,
                        "gemini_errors": gemini_errors,
                        "cache_hits": cache_hits,
                        "cache_checks": cache_checks
                    }
                }
            except Exception:
                pass

        with self._lock:
            avg_latency = round(self._total_latency / self._jobs_processed, 4) if self._jobs_processed > 0 else 0.0
            gemini_error_rate = round(self._gemini_errors / self._gemini_calls, 4) if self._gemini_calls > 0 else 0.0
            cache_hit_rate = round(self._cache_hits / self._cache_checks, 4) if self._cache_checks > 0 else 0.0

            return {
                "jobs_processed": self._jobs_processed,
                "jobs_in_queue": max(0, self._jobs_queued),
                "average_extraction_latency_seconds": avg_latency,
                "gemini_api_error_rate": gemini_error_rate,
                "cache_hit_rate": cache_hit_rate,
                "raw_counters": {
                    "gemini_calls": self._gemini_calls,
                    "gemini_errors": self._gemini_errors,
                    "cache_hits": self._cache_hits,
                    "cache_checks": self._cache_checks
                }
            }

metrics_tracker = MetricsTracker()
