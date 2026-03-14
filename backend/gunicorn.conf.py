"""
Gunicorn configuration for Railway deployment.
Railway sets PORT env var — gunicorn config reads it here
so the start command doesn't need shell variable expansion.
"""
import os

# Server socket
bind = "0.0.0.0:" + os.environ.get("PORT", "5000")

# Worker processes — Railway gives 1-2 vCPUs
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))

# Use gthread for better concurrency with I/O-bound requests
worker_class = "gthread"
threads = int(os.environ.get("GUNICORN_THREADS", "4"))

# Timeouts
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")

# Do NOT preload — ThreadedConnectionPool can't survive fork()
# Each worker initializes its own pool on first request
preload_app = False

# Recycle workers to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50


def post_fork(server, worker):
    """Reset DB pool after fork so each worker gets its own connections."""
    from database.connection import close_pool
    try:
        close_pool()
    except Exception:
        pass
