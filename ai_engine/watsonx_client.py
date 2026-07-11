"""
Library AI Agent - IBM watsonx.ai Studio Client
Wraps IBM watsonx.ai foundation model inference (text generation + embeddings).
Falls back gracefully to rule-based responses when running in demo mode.
"""

import logging
import json
import re
from typing import Optional

from config import watsonx_config, app_config

logger = logging.getLogger(__name__)


class WatsonxClient:
    """
    Thin client for IBM watsonx.ai foundation model APIs.

    In demo/offline mode the class produces deterministic, template-based
    responses so the full agent pipeline can be exercised without live
    IBM Cloud credentials.
    """

    def __init__(self):
        self._client = None
        self._model = None
        self._initialized = False

        if app_config.use_watsonx and not app_config.use_demo_mode:
            self._init_real_client()
        else:
            logger.info("WatsonxClient: running in DEMO mode (no live API calls).")

    # ─────────────────────────────────────────────
    # Initialisation
    # ─────────────────────────────────────────────

    def _init_real_client(self):
        """Initialise the ibm-watsonx-ai Python SDK client."""
        try:
            from ibm_watsonx_ai import APIClient, Credentials
            from ibm_watsonx_ai.foundation_models import ModelInference
            from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

            credentials = Credentials(
                url=watsonx_config.url,
                api_key=watsonx_config.api_key,
            )
            self._client = APIClient(credentials)
            self._model = ModelInference(
                model_id=watsonx_config.default_model,
                api_client=self._client,
                project_id=watsonx_config.project_id,
                params={
                    GenParams.MAX_NEW_TOKENS: watsonx_config.max_new_tokens,
                    GenParams.MIN_NEW_TOKENS: watsonx_config.min_new_tokens,
                    GenParams.TEMPERATURE: watsonx_config.temperature,
                    GenParams.TOP_P: watsonx_config.top_p,
                    GenParams.TOP_K: watsonx_config.top_k,
                    GenParams.REPETITION_PENALTY: watsonx_config.repetition_penalty,
                },
            )
            self._initialized = True
            logger.info("WatsonxClient: connected to IBM watsonx.ai — model %s",
                        watsonx_config.default_model)
        except ImportError:
            logger.warning("ibm-watsonx-ai package not installed — falling back to demo mode.")
            app_config.use_demo_mode = True
        except Exception as exc:
            logger.error("Failed to initialise WatsonxClient: %s — falling back to demo mode.", exc)
            app_config.use_demo_mode = True

    # ─────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────

    def generate_text(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Generate text from a prompt using the configured foundation model."""
        if self._initialized and self._model:
            return self._real_generate(prompt, max_tokens)
        return self._demo_generate(prompt)

    def generate_recommendation_response(
        self,
        query: str,
        books: list,
        student_name: str = "Student",
    ) -> str:
        """Produce a natural-language recommendation narrative."""
        if self._initialized and self._model:
            prompt = self._build_recommendation_prompt(query, books, student_name)
            return self._real_generate(prompt, max_tokens=400)
        return self._demo_recommendation_response(query, books, student_name)

    def generate_availability_response(self, book_title: str, status: dict) -> str:
        """Generate a helpful availability message."""
        if self._initialized and self._model:
            prompt = (
                f"You are a helpful library assistant. A student asked about: '{book_title}'.\n"
                f"Availability: {json.dumps(status, indent=2)}\n"
                "Provide a concise, friendly 2–3 sentence response about the availability "
                "and any waitlist or reservation options."
            )
            return self._real_generate(prompt, max_tokens=150)
        return self._demo_availability_response(book_title, status)

    def generate_chat_response(self, conversation: list, context: dict) -> str:
        """Generate a conversational response given history and context."""
        if self._initialized and self._model:
            prompt = self._build_chat_prompt(conversation, context)
            return self._real_generate(prompt, max_tokens=300)
        return self._demo_chat_response(conversation[-1]["content"] if conversation else "", context)

    # ─────────────────────────────────────────────
    # Real API calls
    # ─────────────────────────────────────────────

    def _real_generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        try:
            result = self._model.generate_text(prompt=prompt)
            if isinstance(result, dict):
                return result.get("generated_text", "").strip()
            return str(result).strip()
        except Exception as exc:
            logger.error("watsonx.ai generate_text failed: %s", exc)
            return self._demo_generate(prompt)

    # ─────────────────────────────────────────────
    # Prompt builders
    # ─────────────────────────────────────────────

    @staticmethod
    def _build_recommendation_prompt(query: str, books: list, student_name: str) -> str:
        book_list = "\n".join(
            f"  {i+1}. \"{b.get('title', '')}\" by {', '.join(a.get('name','') for a in b.get('authors',[]))} "
            f"({b.get('publication_year', 'N/A')})"
            for i, b in enumerate(books[:5])
        )
        return (
            f"You are a knowledgeable library assistant at a university.\n"
            f"Student {student_name} asked: \"{query}\"\n\n"
            f"Based on this query, the following books have been retrieved:\n{book_list}\n\n"
            "Provide a warm, helpful 3–4 sentence recommendation response that explains "
            "why these books are relevant, highlights the most important one, and "
            "encourages the student to explore the resources. Be concise and academic."
        )

    @staticmethod
    def _build_chat_prompt(conversation: list, context: dict) -> str:
        history = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Librarian'}: {m['content']}"
            for m in conversation[-6:]  # last 3 exchanges
        )
        ctx = context.get("relevant_info", "")
        return (
            "You are an intelligent library assistant at a university. "
            "Help students find and access learning resources.\n\n"
            f"Context: {ctx}\n\n"
            f"Conversation:\n{history}\n\nLibrarian:"
        )

    # ─────────────────────────────────────────────
    # Demo / fallback responses
    # ─────────────────────────────────────────────

    @staticmethod
    def _demo_generate(prompt: str) -> str:
        """Simple keyword-driven fallback (no external API needed)."""
        p = prompt.lower()
        if "recommend" in p or "suggest" in p:
            return (
                "Based on your query, I've identified several highly relevant resources in our library. "
                "These books are well-regarded in the field and align with your learning objectives. "
                "I recommend starting with the most recently updated edition for the latest insights."
            )
        if "availability" in p or "available" in p:
            return "I've checked the library catalogue for that resource and have the latest availability information for you."
        if "reserve" in p or "reservation" in p:
            return "I can help you place a reservation. You'll be notified as soon as the item becomes available."
        return (
            "I'm your Library AI Assistant powered by IBM watsonx.ai. "
            "I can help you find books, check availability, make recommendations, "
            "and manage reservations. What would you like to know?"
        )

    @staticmethod
    def _demo_recommendation_response(query: str, books: list, student_name: str) -> str:
        if not books:
            return (
                f"Hi {student_name}! I searched our catalogue for your query about \"{query}\" "
                "but couldn't find exact matches. Try broadening your search terms or "
                "speak with a librarian for personalised assistance."
            )
        top = books[0]
        top_title = top.get("title", "the top result")
        authors = ", ".join(a.get("name", "") for a in top.get("authors", []))
        count = len(books)
        return (
            f"Hi {student_name}! Based on your query about \"{query}\", I found {count} relevant "
            f"resource{'s' if count > 1 else ''} in our library. "
            f"I particularly recommend \"{top_title}\"" + (f" by {authors}" if authors else "") + " — "
            "it's one of the most borrowed and highly-rated books in this area. "
            "The other suggestions below cover complementary perspectives and will deepen your understanding."
        )

    @staticmethod
    def _demo_availability_response(book_title: str, status: dict) -> str:
        available = status.get("available_copies", 0)
        total = status.get("total_copies", 0)
        waitlist = status.get("waitlist_count", 0)

        if available > 0:
            return (
                f"\"{book_title}\" is currently available! "
                f"We have {available} of {total} copies on the shelf. "
                "You can pick it up from the location shown, or I can reserve it for you."
            )
        elif waitlist > 0:
            return (
                f"\"{book_title}\" is currently checked out — all {total} copies are on loan. "
                f"There are {waitlist} students on the waitlist. "
                "I can add you to the queue and notify you when it becomes available."
            )
        else:
            return (
                f"\"{book_title}\" is currently checked out. "
                "You can join the waitlist and I'll notify you as soon as it's returned. "
                "Would you like me to also suggest similar available books?"
            )

    @staticmethod
    def _demo_chat_response(user_message: str, context: dict) -> str:
        m = user_message.lower()
        if any(kw in m for kw in ["hello", "hi", "hey"]):
            return "Hello! I'm your Library AI Assistant. How can I help you find resources today?"
        if "thank" in m:
            return "You're welcome! Feel free to ask if you need any more help with library resources."
        if "bye" in m or "goodbye" in m:
            return "Goodbye! Happy studying. Don't hesitate to return if you need more help."
        relevant_books = context.get("books", [])
        if relevant_books:
            titles = [b.get("title", "") for b in relevant_books[:2]]
            return (
                f"I found some relevant resources for you. "
                f"You might want to start with \"{titles[0]}\""
                + (f" and \"{titles[1]}\"" if len(titles) > 1 else "")
                + ". Would you like more details on availability or similar books?"
            )
        return (
            "I can help you search our library catalogue, check availability, "
            "get personalised recommendations, or manage book reservations. "
            "What would you like to do?"
        )


# Module-level singleton
watsonx_client = WatsonxClient()
