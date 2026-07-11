"""Admin / analytics routes."""

import logging
from flask import Blueprint, jsonify, request

from database.connection import get_db_session
from ai_engine.library_repository import LibraryRepository

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/stats", methods=["GET"])
def library_stats():
    """High-level library statistics."""
    try:
        with get_db_session() as session:
            repo = LibraryRepository(session)
            stats = repo.get_library_stats()
        return jsonify({"success": True, "stats": stats})
    except Exception as exc:
        logger.exception("Stats error")
        return jsonify({"error": str(exc)}), 500


@admin_bp.route("/interactions", methods=["GET"])
def recent_interactions():
    """Return the most recent AI agent interactions."""
    limit = min(int(request.args.get("limit", 20)), 100)
    try:
        from database.models import AgentInteraction
        with get_db_session() as session:
            interactions = (
                session.query(AgentInteraction)
                .order_by(AgentInteraction.created_at.desc())
                .limit(limit)
                .all()
            )
            data = [i.to_dict() for i in interactions]
        return jsonify({"success": True, "interactions": data, "count": len(data)})
    except Exception as exc:
        logger.exception("Interactions error")
        return jsonify({"error": str(exc)}), 500
