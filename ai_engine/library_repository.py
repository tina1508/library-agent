"""
Library AI Agent - Library Search & Data Access Layer
All database queries for books, availability, students, etc.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from database.models import Book, Author, Subject, Student, Course, Loan, Reservation
from database.models import BookStatus, ReservationStatus, LoanStatus

logger = logging.getLogger(__name__)


class LibraryRepository:
    """Data-access layer wrapping SQLAlchemy queries for library operations."""

    def __init__(self, session: Session):
        self.session = session

    # ─────────────────────────────────────────────
    # Book Search
    # ─────────────────────────────────────────────

    def search_books(
        self,
        query: str = "",
        subjects: Optional[list] = None,
        authors: Optional[list] = None,
        publishers: Optional[list] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        available_only: bool = False,
        resource_type: Optional[str] = None,
        sort_by: str = "relevance",
        limit: int = 20,
        offset: int = 0,
    ) -> list:
        """Advanced full-text search across all book metadata fields."""
        q = self.session.query(Book)

        if query:
            terms = query.split()
            conditions = []
            for term in terms:
                t = f"%{term.strip()}%"
                conditions.extend([
                    Book.title.ilike(t),
                    Book.description.ilike(t),
                    Book.publisher.ilike(t),
                    Book.call_number.ilike(t),
                ])
            q = q.filter(or_(*conditions))

        if subjects:
            subject_filters = [Subject.name.ilike(f"%{s}%") for s in subjects]
            q = q.join(Book.subjects).filter(or_(*subject_filters))

        if authors:
            author_filters = [Author.name.ilike(f"%{a}%") for a in authors]
            q = q.join(Book.authors).filter(or_(*author_filters))

        if publishers:
            pub_filters = [Book.publisher.ilike(f"%{p}%") for p in publishers]
            q = q.filter(or_(*pub_filters))

        if year_from:
            q = q.filter(Book.publication_year >= year_from)

        if year_to:
            q = q.filter(Book.publication_year <= year_to)

        if available_only:
            q = q.filter(Book.available_copies > 0)

        if resource_type:
            q = q.filter(Book.resource_type == resource_type)

        if sort_by == "year":
            q = q.order_by(Book.publication_year.desc())
        elif sort_by == "rating":
            q = q.order_by(Book.rating.desc())
        elif sort_by == "popularity":
            q = q.order_by(Book.borrow_count.desc(), Book.demand_score.desc())
        else:
            q = q.order_by(Book.demand_score.desc(), Book.borrow_count.desc())

        return q.distinct().offset(offset).limit(limit).all()

    def search_by_keywords(self, keywords: list, limit: int = 15, sort_by: str = "relevance") -> list:
        """Search books by a list of keyword terms across all text fields."""
        if not keywords:
            return []
        conditions = []
        for kw in keywords:
            term = f"%{kw}%"
            conditions.extend([
                Book.title.ilike(term),
                Book.description.ilike(term),
                Book.publisher.ilike(term),
            ])
        q = self.session.query(Book).filter(or_(*conditions))
        if sort_by == "year":
            q = q.order_by(Book.publication_year.desc())
        elif sort_by == "rating":
            q = q.order_by(Book.rating.desc())
        elif sort_by == "popularity":
            q = q.order_by(Book.borrow_count.desc())
        else:
            q = q.order_by(Book.demand_score.desc(), Book.rating.desc())
        return q.distinct().limit(limit).all()

    def search_by_author(self, author_name: str, limit: int = 15) -> list:
        """Return all books by a given author (fuzzy name match)."""
        return (
            self.session.query(Book)
            .join(Book.authors)
            .filter(Author.name.ilike(f"%{author_name}%"))
            .order_by(Book.publication_year.desc())
            .limit(limit)
            .all()
        )

    def search_by_publisher(self, publisher: str, limit: int = 15) -> list:
        """Return books from a given publisher."""
        return (
            self.session.query(Book)
            .filter(Book.publisher.ilike(f"%{publisher}%"))
            .order_by(Book.publication_year.desc(), Book.demand_score.desc())
            .limit(limit)
            .all()
        )

    def search_by_year_range(self, year_from: int, year_to: int, limit: int = 15) -> list:
        """Return books published within a year range."""
        q = self.session.query(Book)
        if year_from:
            q = q.filter(Book.publication_year >= year_from)
        if year_to:
            q = q.filter(Book.publication_year <= year_to)
        return q.order_by(Book.publication_year.desc()).limit(limit).all()

    def get_new_arrivals(self, limit: int = 10) -> list:
        """Return the most recently added books (by creation date)."""
        return (
            self.session.query(Book)
            .order_by(Book.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_all_books(self, limit: int = 20, offset: int = 0, sort_by: str = "relevance") -> list:
        """List all books with optional sorting."""
        q = self.session.query(Book)
        if sort_by == "year":
            q = q.order_by(Book.publication_year.desc())
        elif sort_by == "rating":
            q = q.order_by(Book.rating.desc().nulls_last())
        elif sort_by == "popularity":
            q = q.order_by(Book.borrow_count.desc())
        else:
            q = q.order_by(Book.demand_score.desc())
        return q.offset(offset).limit(limit).all()

    def get_books_by_subject_names(self, subject_names: list, limit: int = 10) -> list:
        """Retrieve books matching given subject names."""
        if not subject_names:
            return []
        filters = [Subject.name.ilike(f"%{s}%") for s in subject_names]
        return (
            self.session.query(Book)
            .join(Book.subjects)
            .filter(or_(*filters))
            .order_by(Book.demand_score.desc())
            .limit(limit)
            .all()
        )

    def get_high_demand_books(self, limit: int = 10) -> list:
        """Return books with the highest demand scores."""
        return (
            self.session.query(Book)
            .order_by(Book.demand_score.desc(), Book.borrow_count.desc())
            .limit(limit)
            .all()
        )

    def get_book_by_id(self, book_id: str) -> Optional[Book]:
        return self.session.query(Book).filter(Book.id == book_id).first()

    def get_book_by_isbn(self, isbn: str) -> Optional[Book]:
        return self.session.query(Book).filter(Book.isbn == isbn).first()

    def get_book_by_title(self, title: str) -> Optional[Book]:
        return (
            self.session.query(Book)
            .filter(Book.title.ilike(f"%{title}%"))
            .first()
        )

    # ─────────────────────────────────────────────
    # Availability
    # ─────────────────────────────────────────────

    def get_availability(self, book_id: str) -> dict:
        """Return a structured availability snapshot for a book."""
        book = self.get_book_by_id(book_id)
        if not book:
            return {"error": "Book not found"}

        # Count active waitlist positions
        waitlist_count = (
            self.session.query(Reservation)
            .filter(
                Reservation.book_id == book_id,
                Reservation.status == ReservationStatus.ACTIVE,
            )
            .count()
        )

        # Next expected return date
        next_return = None
        if book.available_copies == 0:
            active_loan = (
                self.session.query(Loan)
                .filter(Loan.book_id == book_id, Loan.status == LoanStatus.ACTIVE)
                .order_by(Loan.due_date)
                .first()
            )
            if active_loan:
                next_return = active_loan.due_date.isoformat()

        return {
            "book_id": book_id,
            "title": book.title,
            "status": book.status,
            "total_copies": book.total_copies,
            "available_copies": book.available_copies,
            "waitlist_count": waitlist_count,
            "next_return_date": next_return,
            "location": book.location,
            "call_number": book.call_number,
            "digital_url": book.digital_url,
        }

    # ─────────────────────────────────────────────
    # Student / Profile
    # ─────────────────────────────────────────────

    def get_student_by_id(self, student_id: str) -> Optional[Student]:
        return (
            self.session.query(Student)
            .filter(Student.student_id == student_id)
            .first()
        )

    def get_student_loans(self, student_db_id: str) -> list:
        return (
            self.session.query(Loan)
            .filter(Loan.student_id == student_db_id, Loan.status == LoanStatus.ACTIVE)
            .all()
        )

    def get_student_reservations(self, student_db_id: str) -> list:
        return (
            self.session.query(Reservation)
            .filter(
                Reservation.student_id == student_db_id,
                Reservation.status == ReservationStatus.ACTIVE,
            )
            .all()
        )

    def get_courses_for_student(self, student_db_id: str) -> list:
        student = self.session.query(Student).filter(Student.id == student_db_id).first()
        return student.courses if student else []

    # ─────────────────────────────────────────────
    # Reservations & Loans
    # ─────────────────────────────────────────────

    def create_reservation(
        self,
        student_db_id: str,
        book_id: str,
        expires_days: int = 3,
    ) -> dict:
        """Create a reservation and return summary."""
        from datetime import datetime, timedelta

        # Guard: already reserved?
        existing = (
            self.session.query(Reservation)
            .filter(
                Reservation.student_id == student_db_id,
                Reservation.book_id == book_id,
                Reservation.status == ReservationStatus.ACTIVE,
            )
            .first()
        )
        if existing:
            return {"success": False, "message": "You already have an active reservation for this book."}

        # Guard: max books
        from config import app_config
        active_count = (
            self.session.query(Reservation)
            .filter(
                Reservation.student_id == student_db_id,
                Reservation.status == ReservationStatus.ACTIVE,
            )
            .count()
        )
        if active_count >= app_config.max_books_per_student:
            return {
                "success": False,
                "message": f"You have reached the maximum of {app_config.max_books_per_student} reservations.",
            }

        # Determine queue position
        queue_pos = (
            self.session.query(Reservation)
            .filter(
                Reservation.book_id == book_id,
                Reservation.status == ReservationStatus.ACTIVE,
            )
            .count()
        ) + 1

        reservation = Reservation(
            student_id=student_db_id,
            book_id=book_id,
            expires_at=datetime.utcnow() + timedelta(days=expires_days),
            queue_position=queue_pos,
        )
        self.session.add(reservation)
        self.session.flush()

        # Update book waitlist count
        book = self.get_book_by_id(book_id)
        if book:
            book.waitlist_count = (book.waitlist_count or 0) + 1

        return {
            "success": True,
            "reservation_id": reservation.id,
            "queue_position": queue_pos,
            "expires_at": reservation.expires_at.isoformat(),
            "message": f"Reservation confirmed! You are #{queue_pos} on the waitlist.",
        }

    def renew_loan(self, loan_id: str, student_db_id: str) -> dict:
        """Extend a loan by the configured loan period."""
        from datetime import timedelta
        from config import app_config

        loan = (
            self.session.query(Loan)
            .filter(
                Loan.id == loan_id,
                Loan.student_id == student_db_id,
                Loan.status == LoanStatus.ACTIVE,
            )
            .first()
        )
        if not loan:
            return {"success": False, "message": "Active loan not found."}
        if loan.renewal_count >= app_config.max_renewals:
            return {
                "success": False,
                "message": f"Maximum renewals ({app_config.max_renewals}) reached for this book.",
            }

        loan.due_date = loan.due_date + timedelta(days=app_config.loan_period_days)
        loan.renewal_count += 1
        loan.status = LoanStatus.RENEWED

        return {
            "success": True,
            "loan_id": loan_id,
            "new_due_date": loan.due_date.isoformat(),
            "renewals_remaining": app_config.max_renewals - loan.renewal_count,
            "message": f"Loan renewed successfully. New due date: {loan.due_date.isoformat()}.",
        }

    # ─────────────────────────────────────────────
    # Analytics
    # ─────────────────────────────────────────────

    def get_library_stats(self) -> dict:
        """Return high-level library statistics for the dashboard."""
        total_books = self.session.query(Book).count()
        available_books = self.session.query(Book).filter(Book.available_copies > 0).count()
        total_students = self.session.query(Student).filter(Student.is_active).count()
        active_loans = self.session.query(Loan).filter(Loan.status == LoanStatus.ACTIVE).count()
        active_reservations = (
            self.session.query(Reservation)
            .filter(Reservation.status == ReservationStatus.ACTIVE)
            .count()
        )
        top_books = (
            self.session.query(Book)
            .order_by(Book.borrow_count.desc())
            .limit(5)
            .all()
        )
        return {
            "total_books": total_books,
            "available_books": available_books,
            "total_students": total_students,
            "active_loans": active_loans,
            "active_reservations": active_reservations,
            "top_books": [{"id": b.id, "title": b.title, "borrow_count": b.borrow_count} for b in top_books],
        }
