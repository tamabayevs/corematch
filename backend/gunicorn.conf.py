"""
Gunicorn configuration for Railway deployment.
Railway sets PORT env var — gunicorn config reads it here
so the start command doesn't need shell variable expansion.
"""
import os

# Server socket
bind = "0.0.0.0:" + os.environ.get("PORT", "5000")

# Worker processes
workers = 2
timeout = 120
graceful_timeout = 30

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Preload app for faster worker startup + shared DB init
preload_app = True
