"""
Library AI Agent - Database seed data for demo mode.
Populates the SQLite demo database with realistic sample data.
"""

import logging
from datetime import date, timedelta
from database.connection import get_db_session, init_db
from database.models import (
    Author, Subject, Book, Course, Student, Loan, Reservation,
    BookStatus, ResourceType, LoanStatus
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Sample Data
# ─────────────────────────────────────────────

SUBJECTS = [
    {"name": "Artificial Intelligence", "dewey_code": "006.3"},
    {"name": "Machine Learning", "dewey_code": "006.31"},
    {"name": "Deep Learning", "dewey_code": "006.32"},
    {"name": "Natural Language Processing", "dewey_code": "006.35"},
    {"name": "Data Science", "dewey_code": "005.7"},
    {"name": "Computer Science", "dewey_code": "004"},
    {"name": "Software Engineering", "dewey_code": "005.1"},
    {"name": "Database Systems", "dewey_code": "005.74"},
    {"name": "Mathematics", "dewey_code": "510"},
    {"name": "Statistics", "dewey_code": "519.5"},
    {"name": "Physics", "dewey_code": "530"},
    {"name": "Biology", "dewey_code": "570"},
    {"name": "Business Management", "dewey_code": "658"},
    {"name": "Psychology", "dewey_code": "150"},
    {"name": "Literature", "dewey_code": "800"},
]

AUTHORS = [
    {"name": "Stuart Russell", "nationality": "British"},
    {"name": "Peter Norvig", "nationality": "American"},
    {"name": "Ian Goodfellow", "nationality": "American"},
    {"name": "Yoshua Bengio", "nationality": "Canadian"},
    {"name": "Aaron Courville", "nationality": "Canadian"},
    {"name": "Christopher Bishop", "nationality": "British"},
    {"name": "Aurélien Géron", "nationality": "French"},
    {"name": "Andrew Ng", "nationality": "American"},
    {"name": "Yann LeCun", "nationality": "French"},
    {"name": "Sebastian Raschka", "nationality": "German"},
    {"name": "Wes McKinney", "nationality": "American"},
    {"name": "Jake VanderPlas", "nationality": "American"},
    {"name": "Thomas H. Cormen", "nationality": "American"},
    {"name": "Donald E. Knuth", "nationality": "American"},
    {"name": "Martin Kleppmann", "nationality": "German"},
    {"name": "Robert C. Martin", "nationality": "American"},
    {"name": "Eric Evans", "nationality": "American"},
    {"name": "Chip Huyen", "nationality": "Vietnamese"},
    {"name": "Josh Wills", "nationality": "American"},
    {"name": "Hadley Wickham", "nationality": "New Zealander"},
]

BOOKS_DATA = [
    {
        "title": "Artificial Intelligence: A Modern Approach",
        "isbn": "9780136042594",
        "resource_type": ResourceType.BOOK,
        "publisher": "Pearson",
        "publication_year": 2020,
        "edition": "4th",
        "total_copies": 5,
        "available_copies": 3,
        "location": "Section A - Shelf 3",
        "call_number": "Q335 .R86",
        "description": "The standard text in AI, covering intelligent agents, search, knowledge representation, planning, and machine learning.",
        "keywords": ["artificial intelligence", "agents", "search", "planning", "machine learning"],
        "borrow_count": 142,
        "rating": 4.8,
        "demand_score": 9.2,
        "authors_names": ["Stuart Russell", "Peter Norvig"],
        "subject_names": ["Artificial Intelligence", "Computer Science"],
    },
    {
        "title": "Deep Learning",
        "isbn": "9780262035613",
        "resource_type": ResourceType.BOOK,
        "publisher": "MIT Press",
        "publication_year": 2016,
        "edition": "1st",
        "total_copies": 4,
        "available_copies": 1,
        "location": "Section A - Shelf 4",
        "call_number": "Q325.5 .G66",
        "description": "Comprehensive introduction to deep learning covering neural networks, regularization, optimization, and modern architectures.",
        "keywords": ["deep learning", "neural networks", "backpropagation", "CNN", "RNN"],
        "borrow_count": 118,
        "rating": 4.9,
        "demand_score": 9.5,
        "authors_names": ["Ian Goodfellow", "Yoshua Bengio", "Aaron Courville"],
        "subject_names": ["Deep Learning", "Machine Learning", "Artificial Intelligence"],
    },
    {
        "title": "Pattern Recognition and Machine Learning",
        "isbn": "9780387310732",
        "resource_type": ResourceType.BOOK,
        "publisher": "Springer",
        "publication_year": 2006,
        "edition": "1st",
        "total_copies": 3,
        "available_copies": 2,
        "location": "Section A - Shelf 5",
        "call_number": "Q327 .B57",
        "description": "A comprehensive treatment of probabilistic graphical models and pattern recognition techniques.",
        "keywords": ["pattern recognition", "Bayesian", "SVM", "neural networks", "probabilistic models"],
        "borrow_count": 97,
        "rating": 4.7,
        "demand_score": 8.8,
        "authors_names": ["Christopher Bishop"],
        "subject_names": ["Machine Learning", "Artificial Intelligence"],
    },
    {
        "title": "Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow",
        "isbn": "9781492032649",
        "resource_type": ResourceType.BOOK,
        "publisher": "O'Reilly Media",
        "publication_year": 2022,
        "edition": "3rd",
        "total_copies": 6,
        "available_copies": 4,
        "location": "Section A - Shelf 6",
        "call_number": "Q325.5 .G47",
        "description": "Practical guide to machine learning using Python, Scikit-Learn, Keras, and TensorFlow with hands-on examples.",
        "keywords": ["scikit-learn", "tensorflow", "keras", "python", "machine learning", "practical"],
        "borrow_count": 156,
        "rating": 4.8,
        "demand_score": 9.1,
        "authors_names": ["Aurélien Géron"],
        "subject_names": ["Machine Learning", "Deep Learning"],
    },
    {
        "title": "Python Machine Learning",
        "isbn": "9781789955750",
        "resource_type": ResourceType.BOOK,
        "publisher": "Packt Publishing",
        "publication_year": 2019,
        "edition": "3rd",
        "total_copies": 4,
        "available_copies": 2,
        "location": "Section A - Shelf 7",
        "call_number": "Q325.5 .R37",
        "description": "Machine learning and deep learning with Python, scikit-learn, and PyTorch.",
        "keywords": ["python", "scikit-learn", "pytorch", "machine learning", "deep learning"],
        "borrow_count": 89,
        "rating": 4.6,
        "demand_score": 8.4,
        "authors_names": ["Sebastian Raschka"],
        "subject_names": ["Machine Learning", "Computer Science"],
    },
    {
        "title": "Python for Data Analysis",
        "isbn": "9781491957660",
        "resource_type": ResourceType.BOOK,
        "publisher": "O'Reilly Media",
        "publication_year": 2022,
        "edition": "3rd",
        "total_copies": 5,
        "available_copies": 3,
        "location": "Section B - Shelf 1",
        "call_number": "QA276.45.P98 M35",
        "description": "Data wrangling, analysis, and visualization using Pandas, NumPy, and IPython.",
        "keywords": ["pandas", "numpy", "data analysis", "python", "data wrangling"],
        "borrow_count": 134,
        "rating": 4.7,
        "demand_score": 8.9,
        "authors_names": ["Wes McKinney"],
        "subject_names": ["Data Science", "Computer Science"],
    },
    {
        "title": "Python Data Science Handbook",
        "isbn": "9781491912058",
        "resource_type": ResourceType.BOOK,
        "publisher": "O'Reilly Media",
        "publication_year": 2016,
        "edition": "1st",
        "total_copies": 4,
        "available_copies": 4,
        "location": "Section B - Shelf 2",
        "call_number": "QA76.73.P98 V36",
        "description": "Essential tools for working with data in Python: IPython, NumPy, Pandas, Matplotlib, and Scikit-Learn.",
        "keywords": ["numpy", "pandas", "matplotlib", "scikit-learn", "data science", "python"],
        "borrow_count": 78,
        "rating": 4.6,
        "demand_score": 8.1,
        "authors_names": ["Jake VanderPlas"],
        "subject_names": ["Data Science", "Machine Learning"],
    },
    {
        "title": "Introduction to Algorithms",
        "isbn": "9780262046305",
        "resource_type": ResourceType.BOOK,
        "publisher": "MIT Press",
        "publication_year": 2022,
        "edition": "4th",
        "total_copies": 8,
        "available_copies": 5,
        "location": "Section C - Shelf 1",
        "call_number": "QA76.6 .C662",
        "description": "The classic comprehensive text on algorithms, covering design, analysis, and correctness.",
        "keywords": ["algorithms", "data structures", "complexity", "sorting", "graphs"],
        "borrow_count": 203,
        "rating": 4.9,
        "demand_score": 9.7,
        "authors_names": ["Thomas H. Cormen"],
        "subject_names": ["Computer Science", "Mathematics"],
    },
    {
        "title": "Designing Data-Intensive Applications",
        "isbn": "9781449373320",
        "resource_type": ResourceType.BOOK,
        "publisher": "O'Reilly Media",
        "publication_year": 2017,
        "edition": "1st",
        "total_copies": 3,
        "available_copies": 0,
        "location": "Section C - Shelf 3",
        "call_number": "QA76.9.D3 K54",
        "description": "The big ideas behind reliable, scalable, and maintainable systems.",
        "keywords": ["databases", "distributed systems", "streaming", "data engineering"],
        "borrow_count": 167,
        "rating": 4.9,
        "demand_score": 9.6,
        "status": BookStatus.CHECKED_OUT,
        "authors_names": ["Martin Kleppmann"],
        "subject_names": ["Database Systems", "Computer Science", "Software Engineering"],
    },
    {
        "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
        "isbn": "9780132350884",
        "resource_type": ResourceType.BOOK,
        "publisher": "Prentice Hall",
        "publication_year": 2008,
        "edition": "1st",
        "total_copies": 4,
        "available_copies": 2,
        "location": "Section D - Shelf 1",
        "call_number": "QA76.76.D47 M37",
        "description": "Practical guide to writing clean, readable, and maintainable code.",
        "keywords": ["clean code", "refactoring", "software craftsmanship", "agile"],
        "borrow_count": 91,
        "rating": 4.5,
        "demand_score": 8.3,
        "authors_names": ["Robert C. Martin"],
        "subject_names": ["Software Engineering", "Computer Science"],
    },
    {
        "title": "Designing Machine Learning Systems",
        "isbn": "9781098107963",
        "resource_type": ResourceType.BOOK,
        "publisher": "O'Reilly Media",
        "publication_year": 2022,
        "edition": "1st",
        "total_copies": 2,
        "available_copies": 1,
        "location": "Section A - Shelf 8",
        "call_number": "Q325.5 .H89",
        "description": "An iterative process for production-ready ML applications on the full lifecycle.",
        "keywords": ["MLOps", "production ML", "feature engineering", "model deployment"],
        "borrow_count": 73,
        "rating": 4.7,
        "demand_score": 8.6,
        "authors_names": ["Chip Huyen"],
        "subject_names": ["Machine Learning", "Data Science", "Software Engineering"],
    },
    {
        "title": "Natural Language Processing with Python",
        "isbn": "9780596516499",
        "resource_type": ResourceType.BOOK,
        "publisher": "O'Reilly Media",
        "publication_year": 2009,
        "edition": "1st",
        "total_copies": 3,
        "available_copies": 2,
        "location": "Section A - Shelf 9",
        "call_number": "QA76.87 .B57",
        "description": "NLP with Python's Natural Language Toolkit (NLTK), covering text processing and language analysis.",
        "keywords": ["NLP", "NLTK", "text processing", "tokenization", "parsing", "python"],
        "borrow_count": 82,
        "rating": 4.4,
        "demand_score": 8.0,
        "authors_names": ["Stuart Russell"],
        "subject_names": ["Natural Language Processing", "Artificial Intelligence"],
    },
    {
        "title": "Statistics for Machine Learning",
        "isbn": "9781788295758",
        "resource_type": ResourceType.BOOK,
        "publisher": "Packt Publishing",
        "publication_year": 2017,
        "edition": "1st",
        "total_copies": 3,
        "available_copies": 3,
        "location": "Section E - Shelf 2",
        "call_number": "QA276 .S73",
        "description": "Statistical techniques for building machine learning models with Python.",
        "keywords": ["statistics", "probability", "regression", "classification", "machine learning"],
        "borrow_count": 61,
        "rating": 4.3,
        "demand_score": 7.6,
        "authors_names": ["Sebastian Raschka"],
        "subject_names": ["Statistics", "Machine Learning"],
    },
    {
        "title": "Domain-Driven Design",
        "isbn": "9780321125217",
        "resource_type": ResourceType.BOOK,
        "publisher": "Addison-Wesley",
        "publication_year": 2003,
        "edition": "1st",
        "total_copies": 2,
        "available_copies": 1,
        "location": "Section D - Shelf 3",
        "call_number": "QA76.9.S88 E93",
        "description": "Tackling complexity in the heart of software development.",
        "keywords": ["domain-driven design", "DDD", "software architecture", "bounded context"],
        "borrow_count": 54,
        "rating": 4.6,
        "demand_score": 7.9,
        "authors_names": ["Eric Evans"],
        "subject_names": ["Software Engineering"],
    },
    {
        "title": "IBM Watson: How to Build with Watson",
        "isbn": "9781484241837",
        "resource_type": ResourceType.BOOK,
        "publisher": "Apress",
        "publication_year": 2019,
        "edition": "1st",
        "total_copies": 2,
        "available_copies": 2,
        "location": "Section A - Shelf 10",
        "call_number": "Q335 .W37",
        "description": "Build intelligent applications using IBM Watson's AI services and APIs.",
        "keywords": ["IBM Watson", "AI services", "cloud", "chatbot", "NLU"],
        "borrow_count": 45,
        "rating": 4.3,
        "demand_score": 7.4,
        "authors_names": ["Andrew Ng"],
        "subject_names": ["Artificial Intelligence", "Computer Science"],
    },
]

COURSES_DATA = [
    {
        "code": "CS401",
        "name": "Artificial Intelligence",
        "department": "Computer Science",
        "level": "undergraduate",
        "syllabus_topics": ["search algorithms", "knowledge representation", "machine learning", "neural networks"],
    },
    {
        "code": "CS501",
        "name": "Machine Learning",
        "department": "Computer Science",
        "level": "postgraduate",
        "syllabus_topics": ["supervised learning", "unsupervised learning", "deep learning", "model evaluation"],
    },
    {
        "code": "DS301",
        "name": "Data Science Fundamentals",
        "department": "Data Science",
        "level": "undergraduate",
        "syllabus_topics": ["data wrangling", "exploratory analysis", "visualization", "statistics"],
    },
    {
        "code": "CS301",
        "name": "Algorithms and Data Structures",
        "department": "Computer Science",
        "level": "undergraduate",
        "syllabus_topics": ["sorting", "searching", "graphs", "dynamic programming", "complexity analysis"],
    },
    {
        "code": "SE401",
        "name": "Software Engineering",
        "department": "Software Engineering",
        "level": "undergraduate",
        "syllabus_topics": ["software design", "patterns", "testing", "agile", "clean code"],
    },
]

STUDENTS_DATA = [
    {
        "student_id": "STU001",
        "name": "Alice Johnson",
        "email": "alice.johnson@university.edu",
        "department": "Computer Science",
        "year_of_study": 3,
        "program": "B.Sc. Computer Science",
        "learning_goals": ["master machine learning", "build AI applications", "improve Python skills"],
        "preferred_subjects": ["Machine Learning", "Artificial Intelligence", "Data Science"],
        "courses_codes": ["CS401", "CS501"],
    },
    {
        "student_id": "STU002",
        "name": "Bob Smith",
        "email": "bob.smith@university.edu",
        "department": "Data Science",
        "year_of_study": 2,
        "program": "B.Sc. Data Science",
        "learning_goals": ["learn data analysis", "statistical modeling", "big data"],
        "preferred_subjects": ["Data Science", "Statistics", "Machine Learning"],
        "courses_codes": ["DS301", "CS301"],
    },
    {
        "student_id": "STU003",
        "name": "Carol Williams",
        "email": "carol.williams@university.edu",
        "department": "Computer Science",
        "year_of_study": 4,
        "program": "M.Sc. Artificial Intelligence",
        "learning_goals": ["deep learning research", "NLP", "computer vision"],
        "preferred_subjects": ["Deep Learning", "Natural Language Processing", "Artificial Intelligence"],
        "courses_codes": ["CS501"],
    },
]


def seed_database():
    """Seed the database with sample data (idempotent — skips if already exists)."""
    init_db()

    with get_db_session() as session:
        # Check if already seeded
        if session.query(Book).count() > 0:
            logger.info("Database already seeded — skipping.")
            return

        logger.info("Seeding database with sample data...")

        # 1. Subjects
        subject_map = {}
        for s in SUBJECTS:
            subj = Subject(name=s["name"], dewey_code=s["dewey_code"])
            session.add(subj)
            session.flush()
            subject_map[s["name"]] = subj

        # 2. Authors
        author_map = {}
        for a in AUTHORS:
            auth = Author(name=a["name"], nationality=a["nationality"])
            session.add(auth)
            session.flush()
            author_map[a["name"]] = auth

        # 3. Books
        book_map = {}
        for b in BOOKS_DATA:
            author_names = b.pop("authors_names", [])
            subject_names = b.pop("subject_names", [])
            book = Book(**{k: v for k, v in b.items() if k not in ("authors_names", "subject_names")})
            book.authors = [author_map[n] for n in author_names if n in author_map]
            book.subjects = [subject_map[n] for n in subject_names if n in subject_map]
            if book.available_copies == 0:
                book.status = BookStatus.CHECKED_OUT
            session.add(book)
            session.flush()
            book_map[book.title] = book

        # 4. Courses
        course_map = {}
        for c in COURSES_DATA:
            codes = c.pop("courses_codes", [])
            course = Course(**c)
            session.add(course)
            session.flush()
            course_map[course.code] = course

        # 5. Students
        for s in STUDENTS_DATA:
            codes = s.pop("courses_codes", [])
            student = Student(**s)
            student.courses = [course_map[c] for c in codes if c in course_map]
            session.add(student)
            session.flush()

        logger.info("Database seeded successfully: %d books, %d students, %d courses.",
                    len(BOOKS_DATA), len(STUDENTS_DATA), len(COURSES_DATA))
