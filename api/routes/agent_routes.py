"""Agent interaction routes — the core AI endpoint."""

import uuid
import logging
from flask import Blueprint, request, jsonify

from database.connection import get_db_session
from ai_engine.agent import LibraryAgent
from api.middleware import optional_auth

logger = logging.getLogger(__name__)
agent_bp = Blueprint("agent", __name__)


def _get_session_id(req) -> str:
    return req.headers.get("X-Session-ID") or req.json.get("session_id", str(uuid.uuid4()))


@agent_bp.route("/query", methods=["POST"])
@optional_auth
def query():
    """
    Main agent endpoint.
    Body: { "query": str, "student_id": str (optional), "session_id": str (optional) }
    Accepts optional Bearer token to log search history for authenticated users.
    """
    data = request.get_json(silent=True) or {}
    user_query = data.get("query", "").strip()

    if not user_query:
        return jsonify({"error": "Query is required."}), 400

    student_id = data.get("student_id")
    session_id = _get_session_id(request)

    try:
        with get_db_session() as session:
            agent = LibraryAgent(session)
            result = agent.process_query(
                query=user_query,
                student_id=student_id,
                session_id=session_id,
            )

        # Log to authenticated user's search history
        cu = getattr(request, "current_user", None)
        if cu:
            _log_search(cu["id"], user_query, result.get("intent"), len(result.get("books", [])))

        return jsonify(result)
    except Exception as exc:
        logger.exception("Agent query error")
        return jsonify({"error": str(exc)}), 500


def _log_search(user_id: str, query: str, intent: str, result_count: int):
    try:
        from database.auth_models import SearchHistory
        with get_db_session() as session:
            session.add(SearchHistory(
                user_id=user_id, query=query,
                intent=intent, result_count=result_count,
            ))
    except Exception as exc:
        logger.warning("Search history log failed: %s", exc)


@agent_bp.route("/feedback", methods=["POST"])
def submit_feedback():
    """
    Submit rating feedback for an interaction.
    Body: { "interaction_id": str, "score": int (1-5) }
    """
    from database.models import AgentInteraction
    data = request.get_json(silent=True) or {}
    interaction_id = data.get("interaction_id")
    score = data.get("score")

    if not interaction_id or score is None:
        return jsonify({"error": "interaction_id and score are required."}), 400
    if not (1 <= int(score) <= 5):
        return jsonify({"error": "Score must be between 1 and 5."}), 400

    try:
        with get_db_session() as session:
            interaction = session.query(AgentInteraction).filter(
                AgentInteraction.id == interaction_id
            ).first()
            if not interaction:
                return jsonify({"error": "Interaction not found."}), 404
            interaction.feedback_score = int(score)
        return jsonify({"success": True, "message": "Thank you for your feedback!"})
    except Exception as exc:
        logger.exception("Feedback error")
        return jsonify({"error": str(exc)}), 500


@agent_bp.route("/trending", methods=["GET"])
def trending():
    """Return the top trending books right now."""
    try:
        with get_db_session() as session:
            from ai_engine.recommendation_engine import RecommendationEngine
            engine = RecommendationEngine(session)
            books = engine.recommend_trending(limit=8)
        return jsonify({"success": True, "books": books})
    except Exception as exc:
        logger.exception("Trending error")
        return jsonify({"error": str(exc)}), 500
