"""
Gunicorn configuration for Railway deployment.
Sized for 100 concurrent customers across all workers.

Railway sets PORT env var — gunicorn config reads it here
so the start command doesn't need shell variable expansion.
"""
import os
import multiprocessing

# Server socket
bind = "0.0.0.0:" + os.environ.get("PORT", "5000")

# Worker processes
# Railway containers typically get 1-2 vCPUs.
# Formula: min(2 * CPU + 1, 9) — capped to stay within DB connection limits.
# Each worker gets its own DB pool (20 connections × N workers).
workers = int(os.environ.get("WEB_CONCURRENCY", min(2 * multiprocessing.cpu_count() + 1, 9)))

# Use gthread worker class for better concurrency with I/O-bound requests
# Each worker spawns threads that share the DB pool
worker_class = "gthread"
threads = int(os.environ.get("GUNICORN_THREADS", "4"))

# Timeouts
timeout = 120          # Kill worker if request takes >120s (video upload safety)
graceful_timeout = 30  # Grace period for in-flight requests on restart
keepalive = 5          # Keep connections alive between requests (reduces TCP handshakes)

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")

# Preload app for faster worker startup + shared DB init
preload_app = True

# Max requests per worker before recycling (prevents memory leaks)
max_requests = 1000
max_requests_jitter = 50  # Stagger restarts to avoid thundering herd
