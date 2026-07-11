"""Book catalogue routes."""

import logging
from flask import Blueprint, request, jsonify

from database.connection import get_db_session
from ai_engine.library_repository import LibraryRepository

logger = logging.getLogger(__name__)
books_bp = Blueprint("books", __name__)


@books_bp.route("/search", methods=["GET"])
def search_books():
    """
    Search the catalogue.
    Query params: q, subject, author, available_only, resource_type, limit, offset
    """
    q = request.args.get("q", "")
    subjects = request.args.getlist("subject")
    authors = request.args.getlist("author")
    available_only = request.args.get("available_only", "false").lower() == "true"
    resource_type = request.args.get("resource_type")
    limit = min(int(request.args.get("limit", 20)), 50)
    offset = int(request.args.get("offset", 0))

    try:
        with get_db_session() as session:
            repo = LibraryRepository(session)
            books = repo.search_books(
                query=q,
                subjects=subjects or None,
                authors=authors or None,
                available_only=available_only,
                resource_type=resource_type,
                limit=limit,
                offset=offset,
            )
            return jsonify({
                "success": True,
                "books": [b.to_dict(include_details=True) for b in books],
                "count": len(books),
            })
    except Exception as exc:
        logger.exception("Book search error")
        return jsonify({"error": str(exc)}), 500


@books_bp.route("/<book_id>", methods=["GET"])
def get_book(book_id: str):
    """Retrieve a single book by its UUID."""
    try:
        with get_db_session() as session:
            repo = LibraryRepository(session)
            book = repo.get_book_by_id(book_id)
            if not book:
                return jsonify({"error": "Book not found."}), 404
            avail = repo.get_availability(book.id)
            from ai_engine.recommendation_engine import RecommendationEngine
            engine = RecommendationEngine(session)
            similar = engine.get_similar_books(book_id, limit=4)
            data = book.to_dict(include_details=True)
            data["availability"] = avail
            data["similar_books"] = similar
        return jsonify({"success": True, "book": data})
    except Exception as exc:
        logger.exception("Get book error")
        return jsonify({"error": str(exc)}), 500


@books_bp.route("/<book_id>/availability", methods=["GET"])
def book_availability(book_id: str):
    """Real-time availability check for a specific book."""
    try:
        with get_db_session() as session:
            repo = LibraryRepository(session)
            avail = repo.get_availability(book_id)
        return jsonify({"success": True, "availability": avail})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@books_bp.route("/<book_id>/reserve", methods=["POST"])
def reserve_book(book_id: str):
    """
    Reserve a book for a student.
    Body: { "student_id": str }
    """
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")
    if not student_id:
        return jsonify({"error": "student_id is required."}), 400

    try:
        with get_db_session() as session:
            repo = LibraryRepository(session)
            student = repo.get_student_by_id(student_id)
            if not student:
                return jsonify({"error": "Student not found."}), 404
            result = repo.create_reservation(
                student_db_id=student.id,
                book_id=book_id,
            )
        return jsonify(result), (200 if result["success"] else 400)
    except Exception as exc:
        logger.exception("Reserve book error")
        return jsonify({"error": str(exc)}), 500


@books_bp.route("/trending", methods=["GET"])
def trending_books():
    """Return the most-demanded books."""
    limit = min(int(request.args.get("limit", 10)), 20)
    try:
        with get_db_session() as session:
            repo = LibraryRepository(session)
            books = repo.get_high_demand_books(limit=limit)
        return jsonify({
            "success": True,
            "books": [b.to_dict() for b in books],
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
