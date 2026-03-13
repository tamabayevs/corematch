"""
CoreMatch — WSGI entry point for Gunicorn.
Usage: gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
"""
import os
import logging
from database.schema import create_tables
from database.migrations import run_migrations
from api.app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# Initialize DB schema on startup (before workers fork)
try:
    create_tables()
    run_migrations()
    logging.info("Database schema ready")
except Exception as e:
    logging.error("Failed to initialize database: %s", e)

# Create the app — this is what gunicorn imports as wsgi:app
app = create_app()
