"""
CoreMatch — Main Flask Application
Registers all blueprints, middleware, and security headers.
"""
import os
import logging
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from flask import Flask, jsonify, g, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# Load .env for local development
load_dotenv()

# ──────────────────────────────────────────────────────────────
# Sentry — Initialize before app creation
# ──────────────────────────────────────────────────────────────
sentry_dsn = os.environ.get("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[FlaskIntegration()],
        environment=os.environ.get("SENTRY_ENVIRONMENT", "development"),
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        send_default_pii=False,  # PDPL: never send PII to Sentry
    )


def create_app() -> Flask:
    """Application factory — creates and configures the Flask app."""
    app = Flask(__name__)

    # ──────────────────────────────────────────────────────────
    # Configuration
    # ──────────────────────────────────────────────────────────
    app.config.update(
        SECRET_KEY=os.environ.get("JWT_SECRET", "dev-secret-change-in-production"),
        ENV=os.environ.get("NODE_ENV", "development"),
        # Session cookies (for CSRF double-submit pattern)
        SESSION_COOKIE_SECURE=os.environ.get("NODE_ENV") == "production",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
    )

    # ──────────────────────────────────────────────────────────
    # CORS — Only allow our frontend origins
    # ──────────────────────────────────────────────────────────
    allowed_origins = [
        "https://corematch.vercel.app",
        "https://app.corematch.ai",
    ]
    if app.config["ENV"] == "development":
        allowed_origins.extend([
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
        ])

    CORS(
        app,
        origins=allowed_origins,
        supports_credentials=True,  # Required for httpOnly refresh token cookie
        allow_headers=["Content-Type", "Authorization", "X-XSRF-Token"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )

    # ──────────────────────────────────────────────────────────
    # Rate Limiting — Flask-Limiter with Redis backend
    # ──────────────────────────────────────────────────────────
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=redis_url,
        default_limits=["200 per minute", "2000 per hour"],
        strategy="fixed-window",
    )
    app.extensions["limiter"] = limiter

    # ──────────────────────────────────────────────────────────
    # Security Headers — Applied to every response
    # ──────────────────────────────────────────────────────────
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(self)"

        if os.environ.get("NODE_ENV") == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Basic CSP — candidate pages have camera permissions
        # Override per-route if needed for more specific pages
        if not response.headers.get("Content-Security-Policy"):
            vite_url = os.environ.get("VITE_API_URL", "")
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "media-src blob: https://videos.corematch.ai; "
                f"connect-src 'self' {vite_url}; "
                "frame-ancestors 'none';"
            )
        return response

    # ──────────────────────────────────────────────────────────
    # Disable verbose Werkzeug request logging in production
    # (prevents PII leakage in Railway logs)
    # ──────────────────────────────────────────────────────────
    if os.environ.get("NODE_ENV") == "production":
        werkzeug_logger = logging.getLogger("werkzeug")
        werkzeug_logger.setLevel(logging.ERROR)

    # ──────────────────────────────────────────────────────────
    # Database — Initialize connection pool
    # ──────────────────────────────────────────────────────────
    from database.connection import init_pool, close_pool
    with app.app_context():
        init_pool()

    @app.teardown_appcontext
    def shutdown_pool(exception=None):
        pass  # Pool persists across requests; only close on app shutdown

    # ──────────────────────────────────────────────────────────
    # Register Blueprints
    # ──────────────────────────────────────────────────────────
    from api.auth import auth_bp
    from api.campaigns import campaigns_bp
    from api.candidates import candidates_bp
    from api.public import public_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(campaigns_bp, url_prefix="/api/campaigns")
    app.register_blueprint(candidates_bp, url_prefix="/api/candidates")
    app.register_blueprint(public_bp, url_prefix="/api/public")

    # ──────────────────────────────────────────────────────────
    # Health Check
    # ──────────────────────────────────────────────────────────
    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "service": "corematch-api"}), 200

    # ──────────────────────────────────────────────────────────
    # Global Error Handlers
    # ──────────────────────────────────────────────────────────
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request", "message": str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"error": "Unauthorized"}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"error": "Forbidden"}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify({"error": "Too many requests", "message": str(e.description)}), 429

    @app.errorhandler(500)
    def internal_error(e):
        logging.error("Internal server error: %s", str(e), exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

    return app


# ──────────────────────────────────────────────────────────────
# Run the app
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Initialize DB schema on startup
    from database.schema import create_tables
    try:
        create_tables()
        logging.info("Database schema ready")
    except Exception as e:
        logging.error("Failed to initialize database: %s", e)

    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("NODE_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
