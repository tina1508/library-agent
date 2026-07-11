"""
Library AI Agent - Advanced Core Orchestrator
Handles 15 intents: search, recommend, availability, reserve, renew,
author search, publisher search, year search, book details,
compare books, new arrivals, loan status, profile, return, help.
"""

import logging
import time
import uuid
from typing import Optional
from sqlalchemy.orm import Session

from ai_engine.nlp_processor import nlp_processor, ParsedQuery
from ai_engine.watsonx_client import watsonx_client
from ai_engine.recommendation_engine import RecommendationEngine
from ai_engine.library_repository import LibraryRepository
from database.models import AgentInteraction, Student
from config import app_config

logger = logging.getLogger(__name__)


class LibraryAgent:
    """
    Advanced Library AI Agent orchestrator.

    Routes 15 distinct intents to specialised handlers. Every handler
    returns a uniform response dict with at least:
        success, action, message, and optional books/details fields.
    """

    def __init__(self, session: Session):
        self.session = session
        self.repo = LibraryRepository(session)
        self.rec_engine = RecommendationEngine(session)

    # ─────────────────────────────────────────────
    # Primary entry point
    # ─────────────────────────────────────────────

    def process_query(
        self,
        query: str,
        student_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> dict:
        start_time = time.time()
        session_id = session_id or str(uuid.uuid4())

        parsed = nlp_processor.parse_query(query)
        logger.info("Query: %r | Intent: %s | Authors: %s | Subjects: %s | Year: %s-%s",
                    query, parsed.intent, parsed.authors, parsed.subjects,
                    parsed.year_from, parsed.year_to)

        student = None
        if student_id:
            student = self.repo.get_student_by_id(student_id)

        response = self._route_intent(parsed, student, query)

        elapsed_ms = int((time.time() - start_time) * 1000)
        response["response_time_ms"] = elapsed_ms
        response["session_id"] = session_id
        response["intent"] = parsed.intent
        response["entities"] = {
            "subjects": parsed.subjects,
            "keywords": parsed.keywords[:5],
            "authors": parsed.authors,
            "publishers": parsed.publishers,
            "year_from": parsed.year_from,
            "year_to": parsed.year_to,
            "isbn": parsed.isbn,
        }

        try:
            self._log_interaction(session_id, query, parsed, response, student, elapsed_ms)
        except Exception as exc:
            logger.warning("Failed to log interaction: %s", exc)

        return response

    # ─────────────────────────────────────────────
    # Intent routing
    # ─────────────────────────────────────────────

    def _route_intent(self, parsed: ParsedQuery, student: Optional[Student], raw_query: str) -> dict:
        intent = parsed.intent
        handlers = {
            "recommend_books":    self._handle_recommendation,
            "search_books":       self._handle_search,
            "check_availability": self._handle_availability,
            "reserve_book":       self._handle_reservation,
            "renew_book":         self._handle_renewal,
            "return_book":        self._handle_return_info,
            "check_loan_status":  self._handle_loan_status,
            "get_profile":        self._handle_profile,
            "search_by_author":   self._handle_author_search,
            "search_by_publisher":self._handle_publisher_search,
            "search_by_year":     self._handle_year_search,
            "get_book_details":   self._handle_book_details,
            "compare_books":      self._handle_compare,
            "get_new_arrivals":   self._handle_new_arrivals,
            "general_help":       self._handle_help,
        }
        handler = handlers.get(intent, self._handle_search)
        return handler(parsed, student, raw_query)

    # ─────────────────────────────────────────────
    # Handlers
    # ─────────────────────────────────────────────

    def _handle_search(self, parsed: ParsedQuery, student: Optional[Student], raw_query: str) -> dict:
        """General-purpose book search with all filters applied."""
        limit = parsed.limit_requested or app_config.max_recommendations

        books = self.repo.search_books(
            query=" ".join(parsed.keywords) if not parsed.subjects else "",
            subjects=parsed.subjects or None,
            authors=parsed.authors or None,
            publishers=parsed.publishers or None,
            year_from=parsed.year_from,
            year_to=parsed.year_to,
            sort_by=parsed.sort_by,
            limit=limit,
        )

        # Fallback: if subject search returned nothing, try keyword search
        if not books and parsed.keywords:
            books = self.repo.search_by_keywords(
                parsed.keywords, limit=limit, sort_by=parsed.sort_by
            )

        # Still nothing: return trending
        if not books:
            books = self.repo.get_high_demand_books(limit=limit)

        student_name = student.name.split()[0] if student else "there"
        book_dicts = [b.to_dict(include_details=True) for b in books]
        _attach_availability(self.repo, book_dicts)

        ai_response = watsonx_client.generate_recommendation_response(
            query=raw_query, books=book_dicts, student_name=student_name
        )
        return {
            "success": True,
            "action": "search_books",
            "message": ai_response,
            "books": book_dicts,
            "total_found": len(book_dicts),
            "filters_applied": _describe_filters(parsed),
        }

    def _handle_recommendation(self, parsed: ParsedQuery, student: Optional[Student], raw_query: str) -> dict:
        """Personalised recommendations using 4-dimension scoring."""
        limit = parsed.limit_requested or app_config.max_recommendations
        books = self.rec_engine.recommend(parsed_query=parsed, student=student, limit=limit)

        student_name = student.name.split()[0] if student else "there"
        ai_response = watsonx_client.generate_recommendation_response(
            query=raw_query, books=books, student_name=student_name
        )

        course_books = []
        if student and student.courses:
            course_books = self.rec_engine.get_course_recommendations(student, limit=3)

        return {
            "success": True,
            "action": "recommendation",
            "message": ai_response,
            "books": books,
            "course_recommendations": course_books,
            "total_found": len(books),
        }

    def _handle_author_search(self, parsed: ParsedQuery, student: Optional[Student], raw_query: str) -> dict:
        """Search books by author name."""
        author_names = parsed.authors

        # If NLP missed the author, try to extract from raw query after "by"
        if not author_names and "by" in raw_query.lower():
            import re
            m = re.search(r'\bby\s+([A-Za-z][\w\s]{2,30})', raw_query, re.IGNORECASE)
            if m:
                author_names = [m.group(1).strip()]

        if not author_names:
            # Fall back to keyword-based search
            return self._handle_search(parsed, student, raw_query)

        all_books = []
        for name in author_names:
            found = self.repo.search_by_author(name, limit=parsed.limit_requested or 12)
            all_books.extend(found)

        # Deduplicate
        seen, unique = set(), []
        for b in all_books:
            if b.id not in seen:
                seen.add(b.id)
                unique.append(b)

        book_dicts = [b.to_dict(include_details=True) for b in unique]
        _attach_availability(self.repo, book_dicts)

        author_str = " / ".join(author_names)
        if book_dicts:
            message = (
                f"Found {len(book_dicts)} book(s) by **{author_str}**. "
                "Here are the results ordered by publication year:"
            )
        else:
            message = (
                f"I couldn't find any books by **{author_str}** in our catalogue. "
                "The author name may be slightly different — try a partial name or check the spelling."
            )
        return {
            "success": True,
            "action": "search_by_author",
            "message": message,
            "books": book_dicts,
            "total_found": len(book_dicts),
            "searched_author": author_str,
        }

    def _handle_publisher_search(self, parsed: ParsedQuery, student: Optional[Student], raw_query: str) -> dict:
        """Search books by publisher."""
        publishers = parsed.publishers
        if not publishers and parsed.keywords:
            publishers = parsed.keywords[:1]

        if not publishers:
            return self._handle_search(parsed, student, raw_query)

        all_books = []
        for pub in publishers:
            found = self.repo.search_by_publisher(pub, limit=parsed.limit_requested or 12)
            all_books.extend(found)

        seen, unique = set(), []
        for b in all_books:
            if b.id not in seen:
                seen.add(b.id)
                unique.append(b)

        book_dicts = [b.to_dict(include_details=True) for b in unique]
        _attach_availability(self.repo, book_dicts)

        pub_str = " / ".join(publishers)
        message = (
            f"Found {len(book_dicts)} book(s) from **{pub_str}** in our catalogue."
            if book_dicts else
            f"No books from **{pub_str}** found. Try a different publisher name."
        )
        return {
            "success": True,
            "action": "search_by_publisher",
            "message": message,
            "books": book_dicts,
            "total_found": len(book_dicts),
        }

    def _handle_year_search(self, parsed: ParsedQuery, student: Optional[Student], raw_query: str) -> dict:
        """Search books by publication year range."""
        if not parsed.year_from and not parsed.year_to:
            # Treat as general search with year sort
            parsed.sort_by = "year"
            return self._handle_search(parsed, student, raw_query)

        y_from = parsed.year_from or 1900
        y_to = parsed.year_to or 9999
        books = self.repo.search_by_year_range(y_from, y_to, limit=parsed.limit_requested or 12)

        # If also has subject/keyword filters, re-filter in memory
        if parsed.subjects or parsed.keywords:
            kw_set = {k.lower() for k in (parsed.keywords or [])}
            sub_set = {s.lower() for s in (parsed.subjects or [])}

            def relevant(b):
                text = (b.title + " " + (b.description or "")).lower()
                subj_names = {s.name.lower() for s in (b.subjects or [])}
                kw_match = any(k in text for k in kw_set) if kw_set else True
                sub_match = any(s in sn for s in sub_set for sn in subj_names) if sub_set else True
                return kw_match or sub_match

            books = [b for b in books if relevant(b)]

        book_dicts = [b.to_dict(include_details=True) for b in books]
        _attach_availability(self.repo, book_dicts)

        yr_label = f"{parsed.year_from}" if parsed.year_from == parsed.year_to else \
                   f"{parsed.year_from or 'before'} – {parsed.year_to or 'present'}"
        message = (
            f"Found {len(book_dicts)} book(s) published in **{yr_label}**."
            if book_dicts else
            f"No books found for the year range **{yr_label}**."
        )
        return {
            "success": True,
            "action": "search_by_year",
            "message": message,
            "books": book_dicts,
            "total_found": len(book_dicts),
            "year_range": {"from": parsed.year_from, "to": parsed.year_to},
        }

    def _handle_book_details(self, parsed: ParsedQuery, student: Optional[Student], raw_query: str) -> dict:
        """Return full details for a specific book."""
        book = None

        # ISBN lookup takes priority
        if parsed.isbn:
            book = self.repo.get_book_by_isbn(parsed.isbn)

        # Quoted title
        if not book and parsed.book_titles:
            book = self.repo.get_book_by_title(parsed.book_titles[0])

        # Keyword fallback
        if not book and parsed.keywords:
            results = self.repo.search_by_keywords(parsed.keywords, limit=1)
            if results:
                book = results[0]

        if not book:
            return {
                "success": False,
                "action": "get_book_details",
                "message": "I couldn't find that book. Try quoting the exact title, e.g. `\"Deep Learning\"`, or provide the ISBN.",
                "books": [],
            }

        avail = self.repo.get_availability(book.id)
        similar = self.rec_engine.get_similar_books(book.id, limit=4)
        book_dict = book.to_dict(include_details=True)
        book_dict["availability"] = avail
        book_dict["similar_books"] = similar

        authors_str = ", ".join(a.name for a in (book.authors or []))
        avail_str = (
            f"{avail['available_copies']}/{avail['total_copies']} copies available at {avail.get('location', 'library')}"
            if avail.get("available_copies", 0) > 0
            else f"All copies checked out. Waitlist: {avail.get('waitlist_count', 0)} student(s). "
                 + (f"Next return: {avail['next_return_date']}" if avail.get("next_return_date") else "")
        )

        message = (
            f"**{book.title}**\n"
            + (f"by {authors_str}\n" if authors_str else "")
            + f"Published: {book.publisher or '—'}, {book.publication_year or '—'} · {book.edition or '1st'} edition\n"
            + f"Location: {book.location or '—'} · Call number: {book.call_number or '—'}\n"
            + f"Availability: {avail_str}\n"
            + (f"\n{book.description}" if book.description else "")
        )

        return {
            "success": True,
            "action": "get_book_details",
            "message": message,
            "book": book_dict,
            "books": [book_dict],
            "availability": avail,
        }

    def _handle_compare(self, parsed: ParsedQuery, student: Optional[Student], raw_query: str) -> dict:
        """Side-by-side comparison of two books."""
        titles = parsed.compare_titles or parsed.book_titles

        books = []
        for title in titles[:2]:
            b = self.repo.get_book_by_title(title)
            if b:
                books.append(b)

        # Fallback: search for each keyword cluster
        if len(books) < 2 and parsed.keywords:
            mid = len(parsed.keywords) // 2 or 1
            for chunk in [parsed.keywords[:mid], parsed.keywords[mid:]]:
                results = self.repo.search_by_keywords(chunk, limit=1)
                if results and results[0].id not in [b.id for b in books]:
                    books.append(results[0])

        if len(books) < 2:
            return {
                "success": False,
                "action": "compare_books",
                "message": (
                    "To compare books, please mention both titles. "
                    "Example: `compare \"Deep Learning\" vs \"Pattern Recognition and Machine Learning\"`"
                ),
                "books": [b.to_dict() for b in books],
            }

        book_dicts = [b.to_dict(include_details=True) for b in books[:2]]
        _attach_availability(self.repo, book_dicts)

        a, b_book = book_dicts[0], book_dicts[1]
        a_auth = ", ".join(x["name"] for x in a.get("authors", []))
        b_auth = ", ".join(x["name"] for x in b_book.get("authors", []))
        a_avail = a.get("availability", {})
        b_avail = b_book.get("availability", {})

        message = (
            f"**Comparison: {a['title']} vs {b_book['title']}**\n\n"
            f"**{a['title']}**\n"
            f"  • Authors: {a_auth or '—'}\n"
            f"  • Year: {a.get('publication_year') or '—'} · Edition: {a.get('edition') or '—'}\n"
            f"  • Rating: {a.get('rating') or '—'}/5 · Borrows: {a.get('borrow_count') or 0}\n"
            f"  • Availability: {a_avail.get('available_copies', 0)}/{a_avail.get('total_copies', 0)} copies\n"
            f"  • Subjects: {', '.join(s['name'] for s in a.get('subjects', []))}\n\n"
            f"**{b_book['title']}**\n"
            f"  • Authors: {b_auth or '—'}\n"
            f"  • Year: {b_book.get('publication_year') or '—'} · Edition: {b_book.get('edition') or '—'}\n"
            f"  • Rating: {b_book.get('rating') or '—'}/5 · Borrows: {b_book.get('borrow_count') or 0}\n"
            f"  • Availability: {b_avail.get('available_copies', 0)}/{b_avail.get('total_copies', 0)} copies\n"
            f"  • Subjects: {', '.join(s['name'] for s in b_book.get('subjects', []))}\n\n"
            "Both are excellent resources. Choose based on your current level and specific topic focus."
        )
        return {
            "success": True,
            "action": "compare_books",
            "message": message,
            "books": book_dicts[:2],
            "comparison": True,
        }

    def _handle_new_arrivals(self, parsed: ParsedQuery, student: Optional[Student], raw_query: str) -> dict:
        """Return recently added books."""
        limit = parsed.limit_requested or 8
        books = self.repo.get_new_arrivals(limit=limit)
        book_dicts = [b.to_dict(include_details=True) for b in books]
        _attach_availability(self.repo, book_dicts)
        message = (
            f"Here are the **{len(book_dicts)} newest additions** to our library catalogue! "
            "These were recently acquired and may not be widely known yet."
            if book_dicts else
            "No new arrivals found in the catalogue."
        )
        return {
            "success": True,
            "action": "get_new_arrivals",
            "message": message,
            "books": book_dicts,
            "total_found": len(book_dicts),
        }

    def _handle_availability(self, parsed: ParsedQuery, student: Optional[Student], raw_query: str) -> dict:
        """Check availability of one or more books."""
        results = []

        for title in parsed.book_titles:
            book = self.repo.get_book_by_title(title)
            if book:
                avail = self.repo.get_availability(book.id)
                ai_msg = watsonx_client.generate_availability_response(book.title, avail)
                bd = book.to_dict()
                bd["availability"] = avail
                results.append({"book": bd, "availability": avail, "message": ai_msg})

        if not results and (parsed.keywords or parsed.subjects):
            search_q = " ".join(parsed.keywords) if parsed.keywords else ""
            books = self.repo.search_books(
                query=search_q,
                subjects=parsed.subjects or None,
                limit=5,
            )
            for book in books:
                avail = self.repo.get_availability(book.id)
                ai_msg = watsonx_client.generate_availability_response(book.title, avail)
                bd = book.to_dict()
                bd["availability"] = avail
                results.append({"book": bd, "availability": avail, "message": ai_msg})

        if not results:
            return {
                "success": False,
                "action": "check_availability",
                "message": 'Please specify a book title (e.g. `"Deep Learning"`) or keywords to check availability.',
                "books": [],
            }

        # Build a summary of the primary result
        main = results[0]
        avail0 = main["availability"]
        book_dicts = [r["book"] for r in results]
        summary = main.get("message", f"Found {len(results)} result(s).")
        return {
            "success": True,
            "action": "check_availability",
            "message": summary,
            "books": book_dicts,
            "availability_results": results,
        }

    def _handle_reservation(self, parsed: ParsedQuery, student: Optional[Student], raw_query: str) -> dict:
        if not student:
            return {
                "success": False,
                "action": "reserve_book",
                "message": "Please select a student profile from the sidebar to make a reservation.",
            }

        book = None
        if parsed.book_titles:
            book = self.repo.get_book_by_title(parsed.book_titles[0])
        if not book and parsed.keywords:
            results = self.repo.search_books(query=" ".join(parsed.keywords), limit=1)
            if results:
                book = results[0]

        if not book:
            return {
                "success": False,
                "action": "reserve_book",
                "message": "I couldn't identify the book to reserve. Please mention the title in quotes, e.g. `\"Deep Learning\"`.",
            }

        result = self.repo.create_reservation(student_db_id=student.id, book_id=book.id)
        avail = self.repo.get_availability(book.id)
        book_dict = book.to_dict()
        book_dict["availability"] = avail

        return {
            "success": result["success"],
            "action": "reserve_book",
            "message": result["message"],
            "reservation": result if result["success"] else None,
            "book": book_dict,
            "books": [book_dict],
            "availability": avail,
        }

    def _handle_renewal(self, parsed: ParsedQuery, student: Optional[Student], raw_query: str) -> dict:
        if not student:
            return {
                "success": False,
                "action": "renew_book",
                "message": "Please select a student profile to renew your loans.",
            }

        loans = self.repo.get_student_loans(student.id)
        if not loans:
            return {
                "success": False,
                "action": "renew_book",
                "message": "You don't have any active loans to renew.",
            }

        target_loan = None
        if parsed.book_titles:
            for loan in loans:
                if loan.book and any(t.lower() in loan.book.title.lower() for t in parsed.book_titles):
                    target_loan = loan
                    break
        if not target_loan and parsed.keywords:
            for loan in loans:
                if loan.book and any(k in loan.book.title.lower() for k in parsed.keywords):
                    target_loan = loan
                    break
        if not target_loan:
            target_loan = loans[0]

        result = self.repo.renew_loan(target_loan.id, student.id)
        return {
            "success": result["success"],
            "action": "renew_book",
            "message": result["message"],
            "renewal_details": result if result["success"] else None,
            "book_title": target_loan.book.title if target_loan.book else "Unknown",
        }

    def _handle_return_info(self, parsed: ParsedQuery, student: Optional[Student], raw_query: str) -> dict:
        if not student:
            return {
                "success": False,
                "action": "return_book",
                "message": "Please select a student profile to see your due dates.",
            }

        loans = self.repo.get_student_loans(student.id)
        if not loans:
            return {
                "success": True,
                "action": "return_book",
                "message": "You have no active loans. Nothing to return!",
            }

        lines = []
        for loan in loans:
            title = loan.book.title if loan.book else "Unknown"
            lines.append(f"• **{title}** — due {loan.due_date.isoformat()}")

        message = "Here are your active loans and due dates:\n\n" + "\n".join(lines)
        message += "\n\nTo return a book, please bring it to the library desk. You can also renew it here if you need more time."
        return {
            "success": True,
            "action": "return_book",
            "message": message,
            "loans": [l.to_dict() for l in loans],
        }

    def _handle_loan_status(self, parsed: ParsedQuery, student: Optional[Student], raw_query: str) -> dict:
        if not student:
            return {
                "success": False,
                "action": "check_loan_status",
                "message": "Please select a student profile to view your loans.",
            }

        loans = self.repo.get_student_loans(student.id)
        reservations = self.repo.get_student_reservations(student.id)

        loan_list = []
        for loan in loans:
            ld = loan.to_dict()
            if loan.book:
                ld["book_title"] = loan.book.title
                ld["book"] = loan.book.to_dict()
            loan_list.append(ld)

        res_list = []
        for res in reservations:
            rd = res.to_dict()
            if res.book:
                rd["book_title"] = res.book.title
            res_list.append(rd)

        summary = f"You have **{len(loans)}** active loan(s) and **{len(reservations)}** pending reservation(s)."
        if loans:
            next_due = min(loans, key=lambda l: l.due_date)
            summary += f"\nYour soonest due date is **{next_due.due_date.isoformat()}**"
            if next_due.book:
                summary += f" for *{next_due.book.title}*"
            summary += "."

        return {
            "success": True,
            "action": "check_loan_status",
            "message": summary,
            "loans": loan_list,
            "reservations": res_list,
        }

    def _handle_profile(self, parsed: ParsedQuery, student: Optional[Student], raw_query: str) -> dict:
        if not student:
            return {
                "success": False,
                "action": "get_profile",
                "message": "Please select a student profile from the sidebar.",
            }

        trending = self.rec_engine.recommend_trending(limit=5)
        course_recs = self.rec_engine.get_course_recommendations(student, limit=5)

        return {
            "success": True,
            "action": "get_profile",
            "message": f"Welcome, **{student.name}**! Here's your library profile and personalised recommendations.",
            "profile": student.to_dict(),
            "trending_books": trending,
            "books": course_recs,
        }

    @staticmethod
    def _handle_help(parsed: ParsedQuery, student: Optional[Student], raw_query: str) -> dict:
        help_text = (
            "I'm your **Library AI Assistant**, powered by IBM watsonx.ai! Here's everything I can do:\n\n"
            "📚 **Find books** — `find books about machine learning`\n"
            "🎯 **Recommendations** — `suggest AI books for my semester`\n"
            "👤 **Search by author** — `books by Stuart Russell` or `by Goodfellow`\n"
            "🏢 **Search by publisher** — `books from O'Reilly` or `Springer books`\n"
            "📅 **Search by year** — `books published after 2020` or `from 2015 to 2022`\n"
            "⚖️ **Compare books** — `compare \"Deep Learning\" vs \"Pattern Recognition\"`\n"
            "🔍 **Book details** — `tell me about \"Clean Code\"` or search by ISBN\n"
            "🆕 **New arrivals** — `what new books do you have?`\n"
            "✅ **Availability** — `is \"Deep Learning\" available?`\n"
            "📌 **Reserve / waitlist** — `reserve \"Designing Data-Intensive Applications\"`\n"
            "🔄 **Renew loans** — `renew my book loan`\n"
            "📋 **My loans** — `show my current loans and due dates`\n"
            "👤 **My profile** — `show my profile and reading history`\n\n"
            "💡 **Pro tips:**\n"
            "• Quote exact titles: `\"Introduction to Algorithms\"`\n"
            "• Combine filters: `best rated ML books from 2019`\n"
            "• Ask for a number: `show me top 5 data science books`"
        )
        return {
            "success": True,
            "action": "general_help",
            "message": help_text,
        }

    # ─────────────────────────────────────────────
    # Logging
    # ─────────────────────────────────────────────

    def _log_interaction(self, session_id, query, parsed, response, student, elapsed_ms):
        books_recommended = [b.get("id") for b in response.get("books", [])]
        interaction = AgentInteraction(
            student_id=student.id if student else None,
            session_id=session_id,
            query=query,
            intent=parsed.intent,
            entities={"subjects": parsed.subjects, "keywords": parsed.keywords},
            response=response.get("message", ""),
            books_recommended=books_recommended,
            action_taken=response.get("action"),
            response_time_ms=elapsed_ms,
            model_used=_model_name(),
        )
        self.session.add(interaction)


def _attach_availability(repo: LibraryRepository, book_dicts: list):
    """Attach live availability to a list of book dicts in place."""
    for bd in book_dicts:
        try:
            bd["availability"] = repo.get_availability(bd["id"])
        except Exception:
            pass


def _describe_filters(parsed: ParsedQuery) -> dict:
    """Return a human-readable summary of applied filters."""
    f = {}
    if parsed.subjects:
        f["subjects"] = parsed.subjects
    if parsed.authors:
        f["authors"] = parsed.authors
    if parsed.publishers:
        f["publishers"] = parsed.publishers
    if parsed.year_from or parsed.year_to:
        f["year_range"] = f"{parsed.year_from or '?'} – {parsed.year_to or 'present'}"
    if parsed.sort_by != "relevance":
        f["sorted_by"] = parsed.sort_by
    return f


def _model_name() -> str:
    from config import watsonx_config, app_config
    return "rule-based" if app_config.use_demo_mode else watsonx_config.default_model
