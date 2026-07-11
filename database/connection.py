"""
Library AI Agent - Database Connection & Session Management
Supports IBM Cloud PostgreSQL (Databases for PostgreSQL) and SQLite for demo
"""

import os
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, StaticPool

from .models import Base
# Auth models must be imported so their tables are registered with Base.metadata
import database.auth_models  # noqa: F401
from config import database_config, app_config

logger = logging.getLogger(__name__)


def _build_connection_url() -> str:
    """Build database connection URL from config."""
    if app_config.use_demo_mode:
        # SQLite in-memory for demo / development
        return "sqlite:///./library_demo.db"

    cfg = database_config
    return (
        f"postgresql+psycopg2://{cfg.user}:{cfg.password}"
        f"@{cfg.host}:{cfg.port}/{cfg.name}"
        f"?sslmode={cfg.ssl_mode}"
    )


def _create_engine_instance():
    """Create SQLAlchemy engine with appropriate pool settings."""
    url = _build_connection_url()

    if url.startswith("sqlite"):
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=app_config.debug,
        )
        # Enable WAL mode for better concurrent reads
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, _):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        engine = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=database_config.pool_size,
            max_overflow=database_config.max_overflow,
            pool_pre_ping=True,
            echo=app_config.debug,
        )

    return engine


# Module-level singletons
_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _create_engine_instance()
        logger.info("Database engine created: %s", _engine.url.render_as_string(hide_password=True))
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
        )
    return _SessionLocal


def init_db():
    """Create all tables (idempotent — safe to call on every startup)."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialised.")


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context-manager session with automatic rollback on error."""
    SessionLocal = get_session_factory()
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI / Flask dependency-injection session generator."""
    SessionLocal = get_session_factory()
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def check_db_health() -> dict:
    """Return a health-check dict for the database connection."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "url": engine.url.render_as_string(hide_password=True)}
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}
