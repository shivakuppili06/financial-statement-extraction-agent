"""
worker.py
RQ Worker process entrypoint.
Listens on default Redis queue for incoming PDF extraction jobs.
Run:
  python worker.py
"""

import os
import redis
from rq import Worker, Queue, Connection

listen = ['default']

redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_port = int(os.environ.get("REDIS_PORT", 6379))
conn = redis.Redis(host=redis_host, port=redis_port)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        print(f"RQ Worker listening on host={redis_host}:{redis_port} for queues: {listen}")
        worker.work()
