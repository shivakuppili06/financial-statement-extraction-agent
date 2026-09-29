"""
worker.py
RQ Worker process entrypoint.
Listens on default Redis queue for incoming PDF extraction jobs.
Run:
  python worker.py
"""

import os
import redis
from rq import Worker, Queue

listen = ['default']

redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_port = int(os.environ.get("REDIS_PORT", 6379))
conn = redis.Redis(host=redis_host, port=redis_port)

if __name__ == '__main__':
  try:
    worker = Worker(listen, connection=conn)
    print(f"RQ Worker listening on host={redis_host}:{redis_port} for queues: {listen}")
    worker.work()
  except Exception as e:
    print("Failed to start RQ Worker:", e)
