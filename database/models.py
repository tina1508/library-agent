"""
Library AI Agent - Database Models
SQLAlchemy ORM models for IBM Cloud PostgreSQL / Db2 on Cloud
"""

from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text,
    DateTime, Date, ForeignKey, Table, Enum, JSON,
    create_engine, Index
)
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


# ─────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────

class BookStatus(str, enum.Enum):
    AVAILABLE = "available"
    CHECKED_OUT = "checked_out"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"
    LOST = "lost"


class ReservationStatus(str, enum.Enum):
    ACTIVE = "active"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class LoanStatus(str, enum.Enum):
    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"
    RENEWED = "renewed"


class ResourceType(str, enum.Enum):
    BOOK = "book"
    JOURNAL = "journal"
    E_BOOK = "ebook"
    THESIS = "thesis"
    MAGAZINE = "magazine"
    VIDEO = "video"
    ONLINE_COURSE = "online_course"


# ─────────────────────────────────────────────
# Association Tables
# ─────────────────────────────────────────────

book_authors = Table(
    "book_authors", Base.metadata,
    Column("book_id", String(36), ForeignKey("books.id"), primary_key=True),
    Column("author_id", String(36), ForeignKey("authors.id"), primary_key=True),
)

book_subjects = Table(
    "book_subjects", Base.metadata,
    Column("book_id", String(36), ForeignKey("books.id"), primary_key=True),
    Column("subject_id", String(36), ForeignKey("subjects.id"), primary_key=True),
)

student_courses = Table(
    "student_courses", Base.metadata,
    Column("student_id", String(36), ForeignKey("students.id"), primary_key=True),
    Column("course_id", String(36), ForeignKey("courses.id"), primary_key=True),
)


# ─────────────────────────────────────────────
# Core Models
# ─────────────────────────────────────────────

class Author(Base):
    """Author / creator of library resources."""
    __tablename__ = "authors"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, index=True)
    biography = Column(Text, nullable=True)
    nationality = Column(String(100), nullable=True)
    birth_year = Column(Integer, nullable=True)

    books = relationship("Book", secondary=book_authors, back_populates="authors")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "nationality": self.nationality,
            "birth_year": self.birth_year,
        }


class Subject(Base):
    """Subject / discipline classification."""
    __tablename__ = "subjects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, unique=True, index=True)
    parent_id = Column(String(36), ForeignKey("subjects.id"), nullable=True)
    description = Column(Text, nullable=True)
    dewey_code = Column(String(20), nullable=True)

    books = relationship("Book", secondary=book_subjects, back_populates="subjects")
    children = relationship("Subject", backref="parent", remote_side=[id])

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "dewey_code": self.dewey_code,
            "description": self.description,
        }


class Book(Base):
    """Library resource (book, journal, e-book, etc.)."""
    __tablename__ = "books"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(512), nullable=False, index=True)
    isbn = Column(String(20), nullable=True, unique=True, index=True)
    resource_type = Column(String(30), default=ResourceType.BOOK)
    publisher = Column(String(255), nullable=True)
    publication_year = Column(Integer, nullable=True)
    edition = Column(String(50), nullable=True)
    language = Column(String(50), default="English")
    pages = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    cover_url = Column(String(512), nullable=True)
    location = Column(String(100), nullable=True)   # shelf / section
    call_number = Column(String(50), nullable=True, index=True)
    digital_url = Column(String(512), nullable=True)

    # Inventory
    total_copies = Column(Integer, default=1)
    available_copies = Column(Integer, default=1)
    status = Column(String(30), default=BookStatus.AVAILABLE)

    # Popularity metrics (updated by background job)
    borrow_count = Column(Integer, default=0)
    waitlist_count = Column(Integer, default=0)
    rating = Column(Float, nullable=True)
    demand_score = Column(Float, default=0.0)

    # AI / search metadata
    keywords = Column(JSON, nullable=True)          # extracted keyword list
    embedding_vector = Column(JSON, nullable=True)  # stored as JSON array

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    authors = relationship("Author", secondary=book_authors, back_populates="books")
    subjects = relationship("Subject", secondary=book_subjects, back_populates="books")
    loans = relationship("Loan", back_populates="book")
    reservations = relationship("Reservation", back_populates="book")

    __table_args__ = (
        Index("ix_books_status_available", "status", "available_copies"),
        Index("ix_books_year_type", "publication_year", "resource_type"),
    )

    def to_dict(self, include_details: bool = False):
        data = {
            "id": self.id,
            "title": self.title,
            "isbn": self.isbn,
            "resource_type": self.resource_type,
            "publisher": self.publisher,
            "publication_year": self.publication_year,
            "edition": self.edition,
            "language": self.language,
            "location": self.location,
            "call_number": self.call_number,
            "digital_url": self.digital_url,
            "total_copies": self.total_copies,
            "available_copies": self.available_copies,
            "status": self.status,
            "borrow_count": self.borrow_count,
            "waitlist_count": self.waitlist_count,
            "rating": self.rating,
            "demand_score": self.demand_score,
            "authors": [a.to_dict() for a in (self.authors or [])],
            "subjects": [s.to_dict() for s in (self.subjects or [])],
        }
        if include_details:
            data["description"] = self.description
            data["keywords"] = self.keywords
        return data


class Course(Base):
    """Academic course / module."""
    __tablename__ = "courses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    department = Column(String(100), nullable=True)
    level = Column(String(50), nullable=True)      # undergraduate, postgraduate
    description = Column(Text, nullable=True)
    syllabus_topics = Column(JSON, nullable=True)  # list of topic strings
    required_books = Column(JSON, nullable=True)   # list of book ids

    students = relationship("Student", secondary=student_courses, back_populates="courses")

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "department": self.department,
            "level": self.level,
            "syllabus_topics": self.syllabus_topics or [],
        }


class Student(Base):
    """Student / library member profile."""
    __tablename__ = "students"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    student_id = Column(String(30), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    department = Column(String(100), nullable=True)
    year_of_study = Column(Integer, nullable=True)
    program = Column(String(255), nullable=True)

    # Learning preferences and goals (structured JSON)
    learning_goals = Column(JSON, nullable=True)
    preferred_subjects = Column(JSON, nullable=True)
    reading_history = Column(JSON, nullable=True)   # simplified history cache
    recommendation_history = Column(JSON, nullable=True)

    is_active = Column(Boolean, default=True)
    joined_date = Column(Date, default=date.today)
    last_active = Column(DateTime, nullable=True)

    courses = relationship("Course", secondary=student_courses, back_populates="students")
    loans = relationship("Loan", back_populates="student")
    reservations = relationship("Reservation", back_populates="student")
    interactions = relationship("AgentInteraction", back_populates="student")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "name": self.name,
            "email": self.email,
            "department": self.department,
            "year_of_study": self.year_of_study,
            "program": self.program,
            "learning_goals": self.learning_goals or [],
            "preferred_subjects": self.preferred_subjects or [],
            "courses": [c.to_dict() for c in (self.courses or [])],
        }


class Loan(Base):
    """Physical book loan / checkout record."""
    __tablename__ = "loans"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    student_id = Column(String(36), ForeignKey("students.id"), nullable=False)
    book_id = Column(String(36), ForeignKey("books.id"), nullable=False)
    status = Column(String(20), default=LoanStatus.ACTIVE)
    checked_out_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(Date, nullable=False)
    returned_at = Column(DateTime, nullable=True)
    renewal_count = Column(Integer, default=0)
    notes = Column(Text, nullable=True)

    student = relationship("Student", back_populates="loans")
    book = relationship("Book", back_populates="loans")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "book_id": self.book_id,
            "status": self.status,
            "checked_out_at": self.checked_out_at.isoformat() if self.checked_out_at else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "returned_at": self.returned_at.isoformat() if self.returned_at else None,
            "renewal_count": self.renewal_count,
        }


class Reservation(Base):
    """Book reservation / hold request."""
    __tablename__ = "reservations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    student_id = Column(String(36), ForeignKey("students.id"), nullable=False)
    book_id = Column(String(36), ForeignKey("books.id"), nullable=False)
    status = Column(String(20), default=ReservationStatus.ACTIVE)
    reserved_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    queue_position = Column(Integer, default=1)
    notification_sent = Column(Boolean, default=False)

    student = relationship("Student", back_populates="reservations")
    book = relationship("Book", back_populates="reservations")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "book_id": self.book_id,
            "status": self.status,
            "reserved_at": self.reserved_at.isoformat() if self.reserved_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "queue_position": self.queue_position,
        }


class AgentInteraction(Base):
    """Log of all AI agent interactions for analytics and improvement."""
    __tablename__ = "agent_interactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    student_id = Column(String(36), ForeignKey("students.id"), nullable=True)
    session_id = Column(String(36), nullable=False, index=True)
    query = Column(Text, nullable=False)
    intent = Column(String(100), nullable=True)
    entities = Column(JSON, nullable=True)
    response = Column(Text, nullable=True)
    books_recommended = Column(JSON, nullable=True)   # list of book ids
    action_taken = Column(String(100), nullable=True)
    feedback_score = Column(Integer, nullable=True)   # 1-5 rating
    response_time_ms = Column(Integer, nullable=True)
    model_used = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="interactions")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "session_id": self.session_id,
            "query": self.query,
            "intent": self.intent,
            "response": self.response,
            "books_recommended": self.books_recommended or [],
            "action_taken": self.action_taken,
            "feedback_score": self.feedback_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
