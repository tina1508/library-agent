"""
Library AI Agent - Recommendation Engine
Generates personalised book recommendations by combining:
  - Query relevance (keyword + subject matching)
  - Student profile analysis (courses, learning goals, preferences)
  - Popularity and demand signals
  - Availability preference
"""

import logging
import math
from typing import Optional
from sqlalchemy.orm import Session

from database.models import Student, Book
from ai_engine.library_repository import LibraryRepository
from ai_engine.nlp_processor import ParsedQuery
from config import app_config

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Personalised recommendation engine for library resources.
    Scores candidate books on four dimensions and blends them into a
    final ranked list.
    """

    # Scoring dimension weights
    QUERY_WEIGHT = 0.40       # How well the book matches the query
    PROFILE_WEIGHT = 0.25     # How well the book matches the student profile
    POPULARITY_WEIGHT = 0.20  # Demand / borrow popularity
    AVAILABILITY_WEIGHT = 0.15 # Bonus for currently available books

    def __init__(self, session: Session):
        self.repo = LibraryRepository(session)

    # ─────────────────────────────────────────────
    # Primary entry points
    # ─────────────────────────────────────────────

    def recommend(
        self,
        parsed_query: ParsedQuery,
        student: Optional[Student] = None,
        limit: int = 10,
        available_only: bool = False,
    ) -> list:
        """
        Main recommendation flow:
        1. Retrieve candidates from DB via keyword/subject search
        2. Score each candidate
        3. Return ranked list with score metadata
        """
        candidates = self._fetch_candidates(parsed_query, available_only)

        if not candidates:
            logger.info("No candidates found — falling back to high-demand books.")
            candidates = self.repo.get_high_demand_books(limit=20)

        scored = []
        for book in candidates:
            score_breakdown = self._score_book(book, parsed_query, student)
            total = self._blend_scores(score_breakdown)
            scored.append((total, score_breakdown, book))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for total, breakdown, book in scored[:limit]:
            book_dict = book.to_dict(include_details=True)
            book_dict["recommendation_score"] = round(total, 3)
            book_dict["score_breakdown"] = {k: round(v, 3) for k, v in breakdown.items()}
            book_dict["availability"] = self.repo.get_availability(book.id)
            results.append(book_dict)

        return results

    def get_course_recommendations(self, student: Student, limit: int = 8) -> list:
        """Recommend books aligned with the student's enrolled courses."""
        topics = []
        for course in (student.courses or []):
            topics.extend(course.syllabus_topics or [])
            topics.extend([course.name, course.code])

        if not topics:
            return self.recommend_trending(limit=limit)

        candidates = self.repo.search_by_keywords(topics, limit=30)
        return self._rank_and_format(candidates, limit)

    def get_similar_books(self, book_id: str, limit: int = 5) -> list:
        """Find books similar to a given book by shared subjects/keywords."""
        source = self.repo.get_book_by_id(book_id)
        if not source:
            return []

        subject_names = [s.name for s in (source.subjects or [])]
        keywords = (source.keywords or [])[:5]

        candidates = self.repo.search_books(
            query=" ".join(keywords),
            subjects=subject_names,
            limit=20,
        )
        # Remove the source book itself
        candidates = [b for b in candidates if b.id != book_id]
        return self._rank_and_format(candidates, limit)

    def recommend_trending(self, limit: int = 8) -> list:
        """Return currently trending / high-demand books."""
        books = self.repo.get_high_demand_books(limit=limit)
        return [b.to_dict() for b in books]

    # ─────────────────────────────────────────────
    # Candidate retrieval
    # ─────────────────────────────────────────────

    def _fetch_candidates(self, parsed_query: ParsedQuery, available_only: bool) -> list:
        """Pull a broad candidate set from the database."""
        all_candidates = []

        # 1. Subject-based retrieval
        if parsed_query.subjects:
            subject_books = self.repo.get_books_by_subject_names(parsed_query.subjects, limit=20)
            all_candidates.extend(subject_books)

        # 2. Keyword-based retrieval
        if parsed_query.keywords:
            keyword_books = self.repo.search_by_keywords(parsed_query.keywords, limit=20)
            all_candidates.extend(keyword_books)

        # 3. Title / book-title exact search
        for title in parsed_query.book_titles:
            book = self.repo.get_book_by_title(title)
            if book:
                all_candidates.insert(0, book)

        # 4. Author search
        if parsed_query.authors:
            author_books = self.repo.search_books(authors=parsed_query.authors, limit=10)
            all_candidates.extend(author_books)

        # Deduplicate by id, preserving first-occurrence order
        seen = set()
        deduped = []
        for b in all_candidates:
            if b.id not in seen:
                seen.add(b.id)
                if not available_only or b.available_copies > 0:
                    deduped.append(b)

        return deduped

    # ─────────────────────────────────────────────
    # Scoring
    # ─────────────────────────────────────────────

    def _score_book(
        self,
        book: Book,
        parsed_query: ParsedQuery,
        student: Optional[Student],
    ) -> dict:
        return {
            "query": self._query_score(book, parsed_query),
            "profile": self._profile_score(book, student) if student else 0.5,
            "popularity": self._popularity_score(book),
            "availability": self._availability_score(book),
        }

    def _blend_scores(self, breakdown: dict) -> float:
        return (
            breakdown["query"] * self.QUERY_WEIGHT
            + breakdown["profile"] * self.PROFILE_WEIGHT
            + breakdown["popularity"] * self.POPULARITY_WEIGHT
            + breakdown["availability"] * self.AVAILABILITY_WEIGHT
        )

    @staticmethod
    def _query_score(book: Book, parsed_query: ParsedQuery) -> float:
        """0–1 score: how many query signals appear in the book's metadata."""
        hits = 0.0
        total = 0.0

        title_lower = (book.title or "").lower()
        desc_lower = (book.description or "").lower()
        kw_lower = " ".join(book.keywords or []).lower()

        book_subject_names = {s.name.lower() for s in (book.subjects or [])}
        book_author_names = {a.name.lower() for a in (book.authors or [])}

        # Keyword match (weight 1 each)
        for kw in parsed_query.keywords:
            total += 1
            if kw.lower() in title_lower or kw.lower() in desc_lower or kw.lower() in kw_lower:
                hits += 1

        # Subject match (weight 2 each)
        for subject in parsed_query.subjects:
            total += 2
            if any(subject.lower() in s for s in book_subject_names):
                hits += 2

        # Author match (weight 1.5)
        for author in parsed_query.authors:
            total += 1.5
            if any(author.lower() in a for a in book_author_names):
                hits += 1.5

        # Title match (weight 3)
        for title in parsed_query.book_titles:
            total += 3
            if title.lower() in title_lower:
                hits += 3

        return (hits / total) if total > 0 else 0.3  # default non-zero score

    @staticmethod
    def _profile_score(book: Book, student: Student) -> float:
        """0–1 score: alignment with student's academic profile."""
        if not student:
            return 0.5

        score = 0.0
        book_subject_names = {s.name.lower() for s in (book.subjects or [])}

        # Preferred subjects overlap
        preferred = [s.lower() for s in (student.preferred_subjects or [])]
        matches = sum(1 for p in preferred if any(p in s for s in book_subject_names))
        if preferred:
            score += (matches / len(preferred)) * 0.5

        # Course syllabus overlap
        course_topics = []
        for course in (student.courses or []):
            course_topics.extend([t.lower() for t in (course.syllabus_topics or [])])
            course_topics.append(course.name.lower())

        if course_topics:
            book_text = (
                (book.title or "").lower()
                + " " + " ".join(book.keywords or []).lower()
            )
            topic_hits = sum(1 for t in course_topics if t in book_text)
            score += min(topic_hits / max(len(course_topics), 1), 0.5)

        # Learning goals alignment
        goals = [g.lower() for g in (student.learning_goals or [])]
        if goals:
            book_text = (book.description or "").lower() + " " + (book.title or "").lower()
            goal_hits = sum(1 for g in goals if any(word in book_text for word in g.split()))
            score += min(goal_hits / max(len(goals), 1), 0.2)

        return min(score, 1.0)

    @staticmethod
    def _popularity_score(book: Book) -> float:
        """0–1 normalised popularity score (log scale to dampen outliers)."""
        borrow_count = book.borrow_count or 0
        demand = book.demand_score or 0.0
        rating = book.rating or 3.0

        # Normalise: borrow_count max assumed ~250
        borrow_norm = min(math.log1p(borrow_count) / math.log1p(250), 1.0)
        demand_norm = min(demand / 10.0, 1.0)
        rating_norm = (rating - 1.0) / 4.0  # 1–5 → 0–1

        return borrow_norm * 0.5 + demand_norm * 0.3 + rating_norm * 0.2

    @staticmethod
    def _availability_score(book: Book) -> float:
        """0–1 availability bonus."""
        if book.available_copies > 0:
            return 1.0
        elif book.digital_url:
            return 0.8  # digital always available
        else:
            return 0.2  # penalise checked-out physical copies

    # ─────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────

    def _rank_and_format(self, candidates: list, limit: int) -> list:
        """Simple popularity-based ranking when no query context is available."""
        sorted_books = sorted(
            candidates,
            key=lambda b: (b.demand_score or 0, b.borrow_count or 0),
            reverse=True,
        )
        result = []
        for b in sorted_books[:limit]:
            d = b.to_dict()
            d["availability"] = self.repo.get_availability(b.id)
            result.append(d)
        return result
