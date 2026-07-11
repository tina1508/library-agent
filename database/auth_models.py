"""
Library AI Agent - Auth & User Models
Google OAuth users, JWT sessions, wishlists, reading progress, search history.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text,
    DateTime, ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship
from database.models import Base, generate_uuid


# ─────────────────────────────────────────────
# Google OAuth User
# ─────────────────────────────────────────────

class AuthUser(Base):
    """User authenticated via Google OAuth."""
    __tablename__ = "auth_users"

    id            = Column(String(36),  primary_key=True, default=generate_uuid)
    google_id     = Column(String(128), nullable=False, unique=True, index=True)
    email         = Column(String(255), nullable=False, unique=True, index=True)
    name          = Column(String(255), nullable=False)
    picture       = Column(String(512), nullable=True)   # Google avatar URL
    given_name    = Column(String(128), nullable=True)
    family_name   = Column(String(128), nullable=True)

    # Academic profile (filled after onboarding)
    department    = Column(String(128), nullable=True)
    program       = Column(String(255), nullable=True)
    semester      = Column(Integer,     nullable=True)
    year_of_study = Column(Integer,     nullable=True)
    interests     = Column(JSON,        nullable=True)   # ["AI", "Web", ...]
    learning_goals= Column(JSON,        nullable=True)
    preferred_subjects = Column(JSON,   nullable=True)

    # Linked student record (if exists)
    student_id    = Column(String(36), ForeignKey("students.id"), nullable=True)

    is_active     = Column(Boolean, default=True)
    is_onboarded  = Column(Boolean, default=False)  # completed profile setup
    created_at    = Column(DateTime, default=datetime.utcnow)
    last_login    = Column(DateTime, nullable=True)

    sessions       = relationship("UserSession",      back_populates="user", cascade="all, delete-orphan")
    wishlist_items = relationship("WishlistItem",     back_populates="user", cascade="all, delete-orphan")
    search_history = relationship("SearchHistory",    back_populates="user", cascade="all, delete-orphan")
    reading_history= relationship("ReadingHistory",   back_populates="user", cascade="all, delete-orphan")

    def to_dict(self, include_profile: bool = False):
        d = {
            "id":           self.id,
            "google_id":    self.google_id,
            "email":        self.email,
            "name":         self.name,
            "picture":      self.picture,
            "given_name":   self.given_name,
            "family_name":  self.family_name,
            "is_onboarded": self.is_onboarded,
            "last_login":   self.last_login.isoformat() if self.last_login else None,
        }
        if include_profile:
            d.update({
                "department":          self.department,
                "program":             self.program,
                "semester":            self.semester,
                "year_of_study":       self.year_of_study,
                "interests":           self.interests or [],
                "learning_goals":      self.learning_goals or [],
                "preferred_subjects":  self.preferred_subjects or [],
            })
        return d


# ─────────────────────────────────────────────
# JWT Session tokens
# ─────────────────────────────────────────────

class UserSession(Base):
    """Active JWT session for a logged-in user."""
    __tablename__ = "user_sessions"

    id         = Column(String(36),  primary_key=True, default=generate_uuid)
    user_id    = Column(String(36),  ForeignKey("auth_users.id"), nullable=False, index=True)
    token_hash = Column(String(256), nullable=False, unique=True)  # SHA-256 of JWT
    expires_at = Column(DateTime,    nullable=False)
    created_at = Column(DateTime,    default=datetime.utcnow)
    revoked    = Column(Boolean,     default=False)
    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(64),  nullable=True)

    user = relationship("AuthUser", back_populates="sessions")


# ─────────────────────────────────────────────
# Wishlist / Favourites
# ─────────────────────────────────────────────

class WishlistItem(Base):
    """A book saved to a user's wishlist/favourites."""
    __tablename__ = "wishlist_items"

    id         = Column(String(36), primary_key=True, default=generate_uuid)
    user_id    = Column(String(36), ForeignKey("auth_users.id"), nullable=False, index=True)
    book_id    = Column(String(36), ForeignKey("books.id"),      nullable=False)
    note       = Column(Text,       nullable=True)   # personal note
    added_at   = Column(DateTime,   default=datetime.utcnow)

    user = relationship("AuthUser", back_populates="wishlist_items")
    book = relationship("Book")

    __table_args__ = (
        Index("ix_wishlist_user_book", "user_id", "book_id", unique=True),
    )

    def to_dict(self):
        return {
            "id":       self.id,
            "book_id":  self.book_id,
            "note":     self.note,
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "book":     self.book.to_dict() if self.book else None,
        }


# ─────────────────────────────────────────────
# Search History
# ─────────────────────────────────────────────

class SearchHistory(Base):
    """Log of search queries made by a user."""
    __tablename__ = "search_history"

    id           = Column(String(36), primary_key=True, default=generate_uuid)
    user_id      = Column(String(36), ForeignKey("auth_users.id"), nullable=False, index=True)
    query        = Column(Text,       nullable=False)
    intent       = Column(String(64), nullable=True)
    result_count = Column(Integer,    default=0)
    searched_at  = Column(DateTime,   default=datetime.utcnow)

    user = relationship("AuthUser", back_populates="search_history")

    def to_dict(self):
        return {
            "id":           self.id,
            "query":        self.query,
            "intent":       self.intent,
            "result_count": self.result_count,
            "searched_at":  self.searched_at.isoformat() if self.searched_at else None,
        }


# ─────────────────────────────────────────────
# Reading History / Progress
# ─────────────────────────────────────────────

class ReadingHistory(Base):
    """Tracks books a user has viewed or is reading."""
    __tablename__ = "reading_history"

    id           = Column(String(36), primary_key=True, default=generate_uuid)
    user_id      = Column(String(36), ForeignKey("auth_users.id"), nullable=False, index=True)
    book_id      = Column(String(36), ForeignKey("books.id"),      nullable=False)
    status       = Column(String(32), default="viewed")   # viewed | reading | completed
    progress_pct = Column(Integer,    default=0)          # 0–100
    rating_given = Column(Float,      nullable=True)      # user's personal rating
    started_at   = Column(DateTime,   nullable=True)
    completed_at = Column(DateTime,   nullable=True)
    last_viewed  = Column(DateTime,   default=datetime.utcnow)

    user = relationship("AuthUser", back_populates="reading_history")
    book = relationship("Book")

    __table_args__ = (
        Index("ix_reading_user_book", "user_id", "book_id", unique=True),
    )

    def to_dict(self):
        return {
            "id":           self.id,
            "book_id":      self.book_id,
            "status":       self.status,
            "progress_pct": self.progress_pct,
            "rating_given": self.rating_given,
            "started_at":   self.started_at.isoformat()   if self.started_at   else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "last_viewed":  self.last_viewed.isoformat()  if self.last_viewed  else None,
            "book":         self.book.to_dict()            if self.book         else None,
        }
