"""
rate_limiter.py
Rate limiting and retry handler with exponential backoff for Gemini API calls.
Redis-backed sliding window with in-memory fallback.
"""

import time
import math
import os
import random
import threading
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from resilience.redis_client import get_redis_client

class RateLimitExceededException(Exception):
    pass

class GeminiRateLimiter:
    def __init__(self, max_requests: int = 15, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self.redis_client = get_redis_client()

        self.timestamps = []

    def acquire(self, timeout: float = 10.0) -> bool:
        """Attempts to acquire rate limit slot. Blocks up to timeout seconds if rate limited."""
        start = time.time()
        while time.time() - start < timeout:
            now = time.time()
            if self.redis_client:
                try:
                    pipe = self.redis_client.pipeline()
                    pipe.zadd("ratelimit:gemini", {str(now): now})
                    pipe.zremrangebyscore("ratelimit:gemini", 0, now - self.window_seconds)
                    pipe.zcard("ratelimit:gemini")
                    pipe.expire("ratelimit:gemini", int(self.window_seconds) + 5)
                    res = pipe.execute()
                    current_count = res[2]
                    if current_count <= self.max_requests:
                        return True
                    else:
                        # Revert the added timestamp since limit reached
                        self.redis_client.zrem("ratelimit:gemini", str(now))
                except Exception:
                    pass

            with self._lock:
                self.timestamps = [t for t in self.timestamps if now - t <= self.window_seconds]
                if len(self.timestamps) < self.max_requests:
                    self.timestamps.append(now)
                    return True

            time.sleep(0.05)

        raise RateLimitExceededException("Outbound Gemini API rate limit reached. Request timed out in queue.")

def call_with_retry_and_rate_limit(func, *args, max_retries: int = 4, initial_delay: float = 1.0, **kwargs):
    """
    Executes a callable with rate limiting acquisition and exponential backoff on 429/transient errors.
    """
    rate_limiter = GeminiRateLimiter(max_requests=15, window_seconds=60.0)
    
    for attempt in range(max_retries + 1):
        rate_limiter.acquire(timeout=15.0)
        try:
            return func(*args, **kwargs)
        except Exception as e:
            err_str = str(e).lower()
            # Only retry if explicitly a 429 rate limit or quota exhaustion, not 400/401/403 auth errors
            is_429 = ("429" in err_str or "resourceexhausted" in err_str or "quota exceeded" in err_str) and not ("api_key" in err_str or "invalid" in err_str or "400" in err_str or "403" in err_str)
            if is_429 and attempt < max_retries:
                delay = (initial_delay * (2 ** attempt)) + (random.uniform(0.1, 0.5))
                time.sleep(delay)
                continue
            raise e
