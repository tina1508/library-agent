"""Student profile and loan management routes."""

import logging
from flask import Blueprint, request, jsonify

from database.connection import get_db_session
from ai_engine.library_repository import LibraryRepository
from ai_engine.recommendation_engine import RecommendationEngine
from ai_engine.nlp_processor import ParsedQuery

logger = logging.getLogger(__name__)
student_bp = Blueprint("students", __name__)


@student_bp.route("/<student_id>/profile", methods=["GET"])
def get_profile(student_id: str):
    """Return full student profile."""
    try:
        with get_db_session() as session:
            repo = LibraryRepository(session)
            student = repo.get_student_by_id(student_id)
            if not student:
                return jsonify({"error": "Student not found."}), 404
            loans = repo.get_student_loans(student.id)
            reservations = repo.get_student_reservations(student.id)
            engine = RecommendationEngine(session)
            course_recs = engine.get_course_recommendations(student, limit=5)

            return jsonify({
                "success": True,
                "profile": student.to_dict(),
                "active_loans": [l.to_dict() for l in loans],
                "active_reservations": [r.to_dict() for r in reservations],
                "course_recommendations": course_recs,
            })
    except Exception as exc:
        logger.exception("Get profile error")
        return jsonify({"error": str(exc)}), 500


@student_bp.route("/<student_id>/loans", methods=["GET"])
def get_loans(student_id: str):
    """Return a student's active loans."""
    try:
        with get_db_session() as session:
            repo = LibraryRepository(session)
            student = repo.get_student_by_id(student_id)
            if not student:
                return jsonify({"error": "Student not found."}), 404
            loans = repo.get_student_loans(student.id)
            loan_list = []
            for loan in loans:
                ld = loan.to_dict()
                if loan.book:
                    ld["book"] = loan.book.to_dict()
                loan_list.append(ld)
        return jsonify({"success": True, "loans": loan_list})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@student_bp.route("/<student_id>/loans/<loan_id>/renew", methods=["POST"])
def renew_loan(student_id: str, loan_id: str):
    """Renew a specific loan."""
    try:
        with get_db_session() as session:
            repo = LibraryRepository(session)
            student = repo.get_student_by_id(student_id)
            if not student:
                return jsonify({"error": "Student not found."}), 404
            result = repo.renew_loan(loan_id, student.id)
        return jsonify(result), (200 if result["success"] else 400)
    except Exception as exc:
        logger.exception("Renew loan error")
        return jsonify({"error": str(exc)}), 500


@student_bp.route("/<student_id>/recommendations", methods=["GET"])
def get_recommendations(student_id: str):
    """Get personalised recommendations for a student."""
    q = request.args.get("q", "")
    limit = min(int(request.args.get("limit", 8)), 20)
    try:
        with get_db_session() as session:
            repo = LibraryRepository(session)
            student = repo.get_student_by_id(student_id)
            if not student:
                return jsonify({"error": "Student not found."}), 404
            engine = RecommendationEngine(session)

            if q:
                from ai_engine.nlp_processor import nlp_processor
                parsed = nlp_processor.parse_query(q)
                books = engine.recommend(parsed, student=student, limit=limit)
            else:
                books = engine.get_course_recommendations(student, limit=limit)

        return jsonify({"success": True, "books": books, "student": student.to_dict()})
    except Exception as exc:
        logger.exception("Recommendations error")
        return jsonify({"error": str(exc)}), 500
