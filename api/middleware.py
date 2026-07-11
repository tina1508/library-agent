"""
Library AI Agent - Auth Middleware
request.current_user is set by @require_auth on protected routes.
"""

import logging
from functools import wraps
from flask import request, jsonify
from auth.jwt_utils import verify_token, token_hash
from database.connection import get_db_session
from database.auth_models import UserSession

logger = logging.getLogger(__name__)


def require_auth(f):
    """Decorator: verifies Bearer JWT, injects request.current_user."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        token = None
        if auth.startswith("Bearer "):
            token = auth[7:]
        if not token:
            token = request.args.get("token")

        if not token:
            return jsonify({"error": "Authentication required."}), 401

        payload = verify_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token."}), 401

        # Check token is not revoked in DB
        h = token_hash(token)
        with get_db_session() as session:
            db_sess = session.query(UserSession).filter_by(
                token_hash=h, revoked=False
            ).first()
            if not db_sess:
                return jsonify({"error": "Session not found or revoked."}), 401

        request.current_user = {
            "id":    payload["sub"],
            "email": payload["email"],
        }
        return f(*args, **kwargs)
    return decorated


def optional_auth(f):
    """Decorator: sets request.current_user if token present, else None."""
    @wraps(f)
    def decorated(*args, **kwargs):
        request.current_user = None
        auth = request.headers.get("Authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else request.args.get("token")
        if token:
            payload = verify_token(token)
            if payload:
                request.current_user = {"id": payload["sub"], "email": payload["email"]}
        return f(*args, **kwargs)
    return decorated
