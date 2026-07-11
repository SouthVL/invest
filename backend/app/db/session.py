from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.config import get_database_url

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def create_database_engine(database_url: str | None = None) -> Engine:
    return create_engine(
        database_url or get_database_url(),
        pool_pre_ping=True,
        future=True,
    )


def get_database_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_database_engine()
    return _engine


def create_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine or get_database_engine(),
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory()
    return _session_factory


def get_database_session() -> Generator[Session, None, None]:
    with get_session_factory()() as session:
        yield session
