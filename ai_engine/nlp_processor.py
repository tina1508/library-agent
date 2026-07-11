"""
Library AI Agent - Advanced NLP Processor
Deep query understanding: 15 intents, author/year/publisher/ISBN extraction,
comparison queries, multi-topic requests, sentiment, and context enrichment.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional, List

from config import watson_nlu_config, app_config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────

@dataclass
class ParsedQuery:
    """Structured output of query parsing / NLP analysis."""
    raw_query: str
    intent: str = "search_books"
    confidence: float = 0.0
    entities: dict = field(default_factory=dict)
    keywords: list = field(default_factory=list)
    subjects: list = field(default_factory=list)
    authors: list = field(default_factory=list)
    book_titles: list = field(default_factory=list)
    publishers: list = field(default_factory=list)
    isbn: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    time_constraint: Optional[str] = None
    sentiment: str = "neutral"
    language: str = "en"
    is_question: bool = True
    compare_titles: list = field(default_factory=list)   # for compare_books intent
    limit_requested: int = 10                            # "show me 5 books on..."
    sort_by: str = "relevance"                           # relevance|rating|year|popularity


# ─────────────────────────────────────────────
# Extended Intent taxonomy (15 intents)
# ─────────────────────────────────────────────

INTENTS = {
    "search_books": [
        "find", "search", "look for", "locate", "get books", "show me books",
        "books on", "resources on", "list books", "show books about",
        "any books", "do you have books", "books about", "give me books",
    ],
    "recommend_books": [
        "recommend", "suggest", "what should i read", "best books",
        "good books", "popular books", "top books", "for my course",
        "for my semester", "for studying", "what to read", "reading list",
        "what books", "suggest me", "which books", "what are good",
    ],
    "check_availability": [
        "available", "availability", "is it available", "in stock",
        "on shelf", "can i borrow", "currently available", "do you have",
        "is there a copy", "how many copies", "copies available",
        "can i get", "is it in", "check availability",
    ],
    "reserve_book": [
        "reserve", "reservation", "hold", "put on hold", "book a copy",
        "waitlist", "add me to waitlist", "place a hold", "i want to reserve",
        "can i reserve", "save a copy",
    ],
    "renew_book": [
        "renew", "extend", "renewal", "extend my loan", "more time",
        "keep longer", "extend due date", "renew my book",
    ],
    "return_book": [
        "return", "give back", "hand in", "return date", "when is it due",
        "due date", "when do i return",
    ],
    "check_loan_status": [
        "my loans", "my books", "what i borrowed", "current loans",
        "loan status", "borrowed books", "what do i have", "my borrowings",
        "books i have", "checked out",
    ],
    "get_profile": [
        "my profile", "my account", "my history", "reading history",
        "my recommendations", "my activity", "my stats",
    ],
    "search_by_author": [
        "by author", "books by", "author", "written by", "authored by",
        "from author", "works by", "publications by", "wrote",
    ],
    "search_by_publisher": [
        "publisher", "published by", "from publisher", "oreilly", "pearson",
        "springer", "mit press", "packt", "apress", "addison",
    ],
    "search_by_year": [
        "published in", "from year", "year", "edition", "latest",
        "recent", "newest", "older", "before", "after", "since",
    ],
    "get_book_details": [
        "details about", "tell me about", "info on", "information about",
        "describe", "what is", "summary of", "about the book",
        "isbn", "call number", "where is", "location of",
    ],
    "compare_books": [
        "compare", "difference between", "vs", "versus", "which is better",
        "better book", "which one", "between", "or", "prefer",
    ],
    "get_new_arrivals": [
        "new arrivals", "new books", "recently added", "latest books",
        "new additions", "what's new", "recently acquired",
    ],
    "general_help": [
        "help", "how do i", "what can you", "guide me", "assist",
        "what do you do", "instructions", "commands", "features",
        "capabilities", "what can i ask",
    ],
}

# ─────────────────────────────────────────────
# Expanded subject clusters
# ─────────────────────────────────────────────

SUBJECT_CLUSTERS = {
    "Artificial Intelligence": [
        "ai", "artificial intelligence", "intelligent agent", "expert system",
        "knowledge base", "heuristic", "search algorithm", "planning",
    ],
    "Machine Learning": [
        "machine learning", "ml", "supervised learning", "unsupervised learning",
        "reinforcement learning", "classification", "regression", "clustering",
        "feature engineering", "model training", "overfitting",
    ],
    "Deep Learning": [
        "deep learning", "neural network", "cnn", "rnn", "lstm",
        "transformer", "bert", "gpt", "attention mechanism", "backpropagation",
        "convolutional", "generative", "diffusion model",
    ],
    "Natural Language Processing": [
        "nlp", "natural language", "text processing", "sentiment analysis",
        "tokenization", "named entity", "language model", "text classification",
        "speech recognition", "text generation", "embedding", "word2vec",
    ],
    "Data Science": [
        "data science", "data analysis", "data analytics", "pandas", "numpy",
        "data visualization", "eda", "exploratory analysis", "big data",
        "data pipeline", "feature selection",
    ],
    "Computer Science": [
        "computer science", "programming", "coding", "algorithm",
        "data structure", "complexity", "oop", "functional programming",
        "computer architecture", "os", "operating system",
    ],
    "Software Engineering": [
        "software engineering", "software design", "clean code", "refactoring",
        "testing", "agile", "scrum", "devops", "ci/cd", "microservices",
        "design pattern", "solid principles",
    ],
    "Database Systems": [
        "database", "sql", "nosql", "postgresql", "mongodb", "redis",
        "data storage", "query optimization", "orm", "relational",
        "indexing", "transactions",
    ],
    "Statistics": [
        "statistics", "probability", "statistical analysis", "hypothesis testing",
        "bayesian", "regression analysis", "anova", "distribution",
        "inference", "sampling",
    ],
    "Mathematics": [
        "mathematics", "linear algebra", "calculus", "discrete math",
        "matrix", "vectors", "proof", "graph theory", "number theory",
        "optimization", "differential equations",
    ],
    "Cloud Computing": [
        "cloud", "aws", "azure", "ibm cloud", "gcp", "serverless",
        "kubernetes", "docker", "infrastructure", "saas", "paas",
    ],
    "Cybersecurity": [
        "security", "cybersecurity", "encryption", "hacking", "penetration testing",
        "network security", "vulnerability", "cryptography", "firewall",
    ],
    "Web Development": [
        "web", "html", "css", "javascript", "react", "node", "api",
        "rest", "frontend", "backend", "fullstack", "http",
    ],
    "Business & Management": [
        "business", "management", "entrepreneurship", "strategy", "marketing",
        "finance", "economics", "project management", "leadership",
    ],
    "Physics": [
        "physics", "quantum", "mechanics", "thermodynamics", "relativity",
        "electromagnetism", "optics",
    ],
}

# Known publisher name fragments
KNOWN_PUBLISHERS = [
    "oreilly", "o'reilly", "pearson", "springer", "mit press", "cambridge",
    "packt", "apress", "addison-wesley", "wiley", "mcgraw", "prentice",
    "manning", "no starch", "pragmatic",
]


class NLPProcessor:
    """
    Advanced NLP pipeline for the Library AI Agent.
    Uses IBM Watson NLU in production; falls back to rule-based analysis.
    """

    def __init__(self):
        self._nlu = None
        if app_config.use_watson_nlu and not app_config.use_demo_mode:
            self._init_watson_nlu()
        else:
            logger.info("NLPProcessor: using advanced rule-based pipeline.")

    def _init_watson_nlu(self):
        try:
            from ibm_watson import NaturalLanguageUnderstandingV1
            from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
            authenticator = IAMAuthenticator(watson_nlu_config.api_key)
            self._nlu = NaturalLanguageUnderstandingV1(
                version=watson_nlu_config.version,
                authenticator=authenticator,
            )
            self._nlu.set_service_url(watson_nlu_config.url)
            logger.info("NLPProcessor: connected to IBM Watson NLU.")
        except ImportError:
            logger.warning("ibm-watson not installed — using rule-based NLP.")
        except Exception as exc:
            logger.error("Watson NLU init failed: %s", exc)

    # ─────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────

    def parse_query(self, query: str) -> ParsedQuery:
        parsed = ParsedQuery(raw_query=query)
        if self._nlu:
            self._watson_parse(query, parsed)
        else:
            self._rule_based_parse(query, parsed)
        return parsed

    # ─────────────────────────────────────────────
    # Watson NLU path
    # ─────────────────────────────────────────────

    def _watson_parse(self, query: str, parsed: ParsedQuery):
        try:
            from ibm_watson.natural_language_understanding_v1 import (
                Features, KeywordsOptions, EntitiesOptions, SentimentOptions,
            )
            response = self._nlu.analyze(
                text=query,
                features=Features(
                    keywords=KeywordsOptions(limit=15),
                    entities=EntitiesOptions(limit=15),
                    sentiment=SentimentOptions(),
                ),
            ).get_result()

            parsed.keywords = [
                kw["text"].lower()
                for kw in response.get("keywords", [])
                if kw.get("relevance", 0) > 0.4
            ]
            entities = {}
            for ent in response.get("entities", []):
                ent_type = ent.get("type", "Other")
                entities.setdefault(ent_type, []).append(ent.get("text", ""))
            parsed.entities = entities
            parsed.authors = entities.get("Person", [])
            sentiment_label = (
                response.get("sentiment", {})
                .get("document", {})
                .get("label", "neutral")
            )
            parsed.sentiment = sentiment_label
        except Exception as exc:
            logger.warning("Watson NLU parse failed: %s — falling back.", exc)

        self._rule_based_enrich(query, parsed)

    # ─────────────────────────────────────────────
    # Rule-based path
    # ─────────────────────────────────────────────

    def _rule_based_parse(self, query: str, parsed: ParsedQuery):
        q = query.lower().strip()

        # Score every intent
        best_intent, best_score = "search_books", 0
        scores = {}
        for intent, patterns in INTENTS.items():
            score = sum(2 if len(p) > 8 else 1 for p in patterns if p in q)
            scores[intent] = score
            if score > best_score:
                best_intent, best_score = intent, score

        # Tie-breaking: author cue beats generic search
        if scores.get("search_by_author", 0) > 0 and "by" in q:
            best_intent = "search_by_author"
        if scores.get("compare_books", 0) > 0 and ("vs" in q or " or " in q):
            best_intent = "compare_books"

        parsed.intent = best_intent
        parsed.confidence = min(best_score / 4.0, 1.0)

        self._rule_based_enrich(query, parsed)

    def _rule_based_enrich(self, query: str, parsed: ParsedQuery):
        q = query.lower()

        # ── Intent fallback ──────────────────────────────────
        if parsed.confidence < 0.3:
            for intent, patterns in INTENTS.items():
                if any(p in q for p in patterns):
                    parsed.intent = intent
                    parsed.confidence = 0.6
                    break

        # ── Quoted title extraction ──────────────────────────
        titles = re.findall(r'"([^"]+)"', query)
        if not titles:
            titles = re.findall(r"'([^']+)'", query)
        parsed.book_titles = titles

        # ── Compare: extract two titles  ────────────────────
        if parsed.intent == "compare_books" and not titles:
            # "compare X and Y" / "X vs Y" / "X or Y"
            m = re.search(r'(?:compare|between)\s+(.+?)\s+(?:and|vs|versus)\s+(.+)', q)
            if not m:
                m = re.search(r'(.+?)\s+(?:vs|versus|or)\s+(.+)', q)
            if m:
                parsed.compare_titles = [m.group(1).strip(), m.group(2).strip()]
            elif titles and len(titles) >= 2:
                parsed.compare_titles = titles[:2]

        # ── Author extraction ────────────────────────────────
        if not parsed.authors:
            # "by Stuart Russell" / "books by Goodfellow"
            author_match = re.search(
                r'\bby\s+([A-Z][a-z]+(?: [A-Z][a-z]+){0,3})', query
            )
            if author_match:
                parsed.authors = [author_match.group(1)]
            # "author: Russell" / "author Russell"
            author_match2 = re.search(r'\bauthor[:\s]+([A-Z][a-z]+(?: [A-Z][a-z]+){0,2})', query)
            if author_match2 and not parsed.authors:
                parsed.authors = [author_match2.group(1)]

        # ── ISBN extraction ──────────────────────────────────
        isbn_match = re.search(r'\b(97[89][0-9]{10}|[0-9]{9}[0-9Xx])\b', query)
        if isbn_match:
            parsed.isbn = isbn_match.group(1)

        # ── Publisher extraction ─────────────────────────────
        for pub in KNOWN_PUBLISHERS:
            if pub in q:
                parsed.publishers.append(pub)

        # ── Year / date range extraction ─────────────────────
        # "published after 2018", "from 2015 to 2020", "since 2019", "before 2010"
        year_range = re.search(r'(\d{4})\s+to\s+(\d{4})', q)
        if year_range:
            parsed.year_from = int(year_range.group(1))
            parsed.year_to = int(year_range.group(2))
        else:
            after_m = re.search(r'(?:after|since|from)\s+(\d{4})', q)
            if after_m:
                parsed.year_from = int(after_m.group(1))
            before_m = re.search(r'(?:before|until|up to)\s+(\d{4})', q)
            if before_m:
                parsed.year_to = int(before_m.group(1))
            single_year = re.search(r'(?:in|year)\s+(\d{4})', q)
            if single_year and not parsed.year_from:
                y = int(single_year.group(1))
                parsed.year_from = y
                parsed.year_to = y

        # ── Limit extraction: "show me 5 books" ─────────────
        limit_m = re.search(r'\b(top|show\s+me|find|get)\s+(\d+)\b', q)
        if limit_m:
            parsed.limit_requested = min(int(limit_m.group(2)), 20)

        # ── Sort preference ──────────────────────────────────
        if any(w in q for w in ["latest", "newest", "recent", "new"]):
            parsed.sort_by = "year"
        elif any(w in q for w in ["popular", "most borrowed", "trending", "top"]):
            parsed.sort_by = "popularity"
        elif any(w in q for w in ["rated", "best rated", "highest rated"]):
            parsed.sort_by = "rating"

        # ── Subject detection ────────────────────────────────
        detected = []
        for subject, keywords in SUBJECT_CLUSTERS.items():
            if any(kw in q for kw in keywords):
                detected.append(subject)
        parsed.subjects = detected

        # ── Keyword extraction ───────────────────────────────
        if not parsed.keywords:
            stopwords = {
                "i", "me", "my", "the", "a", "an", "is", "are", "was", "were",
                "for", "on", "in", "of", "to", "and", "or", "but", "it", "its",
                "this", "that", "what", "how", "can", "do", "you", "some", "any",
                "be", "by", "at", "from", "with", "about", "suggest", "find",
                "get", "need", "want", "help", "please", "show", "give", "tell",
                "list", "book", "books", "look",
            }
            tokens = re.findall(r'\b[a-zA-Z]{3,}\b', query)
            parsed.keywords = [t.lower() for t in tokens if t.lower() not in stopwords][:12]

        # ── Time constraints ─────────────────────────────────
        for pattern in [r'\bthis semester\b', r'\bnext semester\b',
                        r'\bfor my course\b', r'\bthis term\b', r'\bfor exam\b']:
            if re.search(pattern, q):
                parsed.time_constraint = re.search(pattern, q).group()
                break

        # ── Subject fallback from keywords ───────────────────
        if not parsed.subjects:
            kw_set = set(parsed.keywords)
            for subject, kws in SUBJECT_CLUSTERS.items():
                if kw_set & set(kws):
                    parsed.subjects.append(subject)

        parsed.is_question = q.endswith("?") or any(
            q.startswith(w) for w in ["what", "which", "where", "how", "can", "do", "is", "are"]
        )

    @staticmethod
    def extract_search_terms(parsed: ParsedQuery) -> list:
        terms = []
        terms.extend(parsed.book_titles)
        terms.extend(parsed.compare_titles)
        terms.extend(parsed.subjects)
        terms.extend(parsed.authors)
        terms.extend(parsed.publishers)
        terms.extend(parsed.keywords)
        seen, result = set(), []
        for t in terms:
            tl = t.lower()
            if tl not in seen:
                seen.add(tl)
                result.append(t)
        return result


# Module-level singleton
nlp_processor = NLPProcessor()
