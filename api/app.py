"""
Library AI Agent - Flask REST API
Exposes all agent capabilities over HTTP.
"""

import logging
import uuid
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from config import app_config
from database.connection import init_db, check_db_health, get_db_session
from database.seed import seed_database
from ai_engine.agent import LibraryAgent
from ai_engine.library_repository import LibraryRepository
from ai_engine.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Application factory."""
    app = Flask(__name__, static_folder="../frontend", static_url_path="")
    app.config["SECRET_KEY"] = app_config.secret_key
    app.config["JSON_SORT_KEYS"] = False
    CORS(app, origins=app_config.cors_origins, supports_credentials=True)

    # ── Bootstrap database ────────────────────────────────
    with app.app_context():
        seed_database()

    # ── Register blueprints ───────────────────────────────
    from api.routes.agent_routes import agent_bp
    from api.routes.books_routes import books_bp
    from api.routes.student_routes import student_bp
    from api.routes.admin_routes import admin_bp
    from api.routes.auth_routes import auth_bp

    app.register_blueprint(agent_bp,  url_prefix="/api/agent")
    app.register_blueprint(books_bp,  url_prefix="/api/books")
    app.register_blueprint(student_bp,url_prefix="/api/students")
    app.register_blueprint(admin_bp,  url_prefix="/api/admin")
    app.register_blueprint(auth_bp,   url_prefix="/api/auth")

    # ── Health check ──────────────────────────────────────
    @app.route("/api/health")
    def health():
        db_status = check_db_health()
        return jsonify({
            "status": "ok",
            "demo_mode": app_config.use_demo_mode,
            "watsonx_enabled": app_config.use_watsonx,
            "watson_nlu_enabled": app_config.use_watson_nlu,
            "database": db_status,
        })

    # ── Serve frontend SPA ────────────────────────────────
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        if path and (path.startswith("api/") or path == "api"):
            return jsonify({"error": "Not found"}), 404
        return send_from_directory(app.static_folder, "index.html")

    # ── Error handlers ────────────────────────────────────
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request", "detail": str(e)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.exception("Unhandled server error")
        return jsonify({"error": "Internal server error"}), 500

    return app
