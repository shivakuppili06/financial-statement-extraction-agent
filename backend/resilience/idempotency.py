"""
idempotency.py
SHA-256 Document hashing and idempotency cache manager.
Stores and retrieves document extraction results to avoid redundant API processing.
"""

import hashlib
import json
import os
import threading
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from observability.metrics import metrics_tracker
from resilience.redis_client import get_redis_client

class IdempotencyManager:
    def __init__(self, ttl_seconds: int = 86400):
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self.redis_client = get_redis_client()

        self._in_memory_cache = {}

    def compute_hash(self, file_bytes: bytes) -> str:
        """Computes SHA-256 digest of file content bytes."""
        return hashlib.sha256(file_bytes).hexdigest()

    def get_cached_result(self, file_hash: str) -> dict:
        """Looks up existing extraction result for the file hash."""
        hit = False
        cached_data = None

        if self.redis_client:
            try:
                val = self.redis_client.get(f"idempotency:{file_hash}")
                if val:
                    hit = True
                    cached_data = json.loads(val.decode('utf-8'))
            except Exception:
                pass
        else:
            with self._lock:
                if file_hash in self._in_memory_cache:
                    hit = True
                    cached_data = self._in_memory_cache[file_hash]

        metrics_tracker.record_cache_check(hit=hit)
        return cached_data

    def cache_result(self, file_hash: str, result: dict):
        """Caches extraction result under the SHA-256 file hash."""
        json_str = json.dumps(result)
        if self.redis_client:
            try:
                self.redis_client.setex(f"idempotency:{file_hash}", self.ttl_seconds, json_str)
                return
            except Exception:
                pass

        with self._lock:
            self._in_memory_cache[file_hash] = result

idempotency_manager = IdempotencyManager()
