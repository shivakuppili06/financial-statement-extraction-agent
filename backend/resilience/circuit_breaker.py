"""
circuit_breaker.py
Circuit Breaker pattern implementation for external service dependencies (Gemini API).
Prevents cascading failures by opening the circuit after threshold failures within a time window.
"""

import time
import threading
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from resilience.redis_client import get_redis_client

class CircuitBreakerOpenException(Exception):
    """Raised when an operation is attempted while the circuit breaker is OPEN."""
    pass

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0, window_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self.redis_client = get_redis_client()

        # In-memory state fallback
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.failure_timestamps = []
        self.last_state_change = time.time()

    def record_failure(self):
        now = time.time()
        if self.redis_client:
            try:
                pipe = self.redis_client.pipeline()
                pipe.zadd("cb:failures", {str(now): now})
                pipe.zremrangebyscore("cb:failures", 0, now - self.window_seconds)
                pipe.zcard("cb:failures")
                res = pipe.execute()
                fail_count = res[2]

                if fail_count >= self.failure_threshold:
                    self.redis_client.set("cb:state", "OPEN")
                    self.redis_client.set("cb:last_open", str(now))
                return
            except Exception:
                pass

        with self._lock:
            self.failure_timestamps = [t for t in self.failure_timestamps if now - t <= self.window_seconds]
            self.failure_timestamps.append(now)
            if len(self.failure_timestamps) >= self.failure_threshold:
                self.state = "OPEN"
                self.last_state_change = now

    def record_success(self):
        now = time.time()
        if self.redis_client:
            try:
                self.redis_client.set("cb:state", "CLOSED")
                self.redis_client.delete("cb:failures")
                return
            except Exception:
                pass

        with self._lock:
            self.state = "CLOSED"
            self.failure_timestamps = []
            self.last_state_change = now

    def check_allow_request(self):
        now = time.time()
        if self.redis_client:
            try:
                cb_state = self.redis_client.get("cb:state")
                state_str = cb_state.decode('utf-8') if cb_state else "CLOSED"
                if state_str == "OPEN":
                    last_open = self.redis_client.get("cb:last_open")
                    last_open_time = float(last_open) if last_open else 0.0
                    if now - last_open_time > self.recovery_timeout:
                        self.redis_client.set("cb:state", "HALF_OPEN")
                        return True
                    else:
                        raise CircuitBreakerOpenException(
                            f"Gemini API circuit breaker is OPEN. Cooldown active ({int(self.recovery_timeout - (now - last_open_time))}s remaining)."
                        )
                return True
            except CircuitBreakerOpenException:
                raise
            except Exception:
                pass

        with self._lock:
            if self.state == "OPEN":
                if now - self.last_state_change > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    return True
                else:
                    raise CircuitBreakerOpenException(
                        f"Gemini API circuit breaker is OPEN. Cooldown active ({int(self.recovery_timeout - (now - self.last_state_change))}s remaining)."
                    )
            return True

gemini_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0, window_seconds=60.0)
