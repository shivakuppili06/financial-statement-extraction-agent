"""
redis_client.py
Centralized Redis connection factory with fast failover when Redis is offline.
"""

import os
import redis

_redis_checked = False
_redis_instance = None

def get_redis_client():
    global _redis_checked, _redis_instance
    if _redis_checked:
        return _redis_instance

    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = int(os.environ.get("REDIS_PORT", 6379))
    
    try:
        r = redis.Redis(host=redis_host, port=redis_port, socket_connect_timeout=0.2, socket_timeout=0.2)
        r.ping()
        _redis_instance = r
    except Exception:
        _redis_instance = None

    _redis_checked = True
    return _redis_instance
