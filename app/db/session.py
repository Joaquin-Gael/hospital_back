"""Database engine and session utilities."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Callable

from sqlmodel import Session, create_engine

from app.config import db_url

if not db_url:
    raise RuntimeError("Database URL is not configured.")

engine = create_engine(db_url, echo=False, future=True, pool_pre_ping=True)

SessionFactory = Callable[[], Session]


def session_factory() -> Session:
    """Return a new SQLModel session bound to the global engine."""
    return Session(engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a managed SQLModel session."""
    with session_factory() as session:
        yield session


__all__ = ["engine", "session_factory", "get_session", "SessionFactory", "db_url"]
