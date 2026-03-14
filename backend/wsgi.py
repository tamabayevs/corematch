"""
CoreMatch — WSGI entry point for Gunicorn.
Usage: gunicorn wsgi:app
"""
import logging
from api.app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# Create the app — this is what gunicorn imports as wsgi:app
# DB schema/migrations run inside create_app() on first request per worker
app = create_app()
