from __future__ import annotations

from sqlalchemy.engine import Engine

from app.db.base import Base
from app.db.config import database_name, get_database_url, mask_database_url
from app.db.session import create_database_engine, create_session_factory


def test_database_url_comes_from_environment(monkeypatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://south_invest:secret-password@db:5432/south_invest_test",
    )

    assert get_database_url() == "postgresql+psycopg://south_invest:secret-password@db:5432/south_invest_test"
    assert database_name() == "south_invest_test"


def test_database_url_masking_hides_password() -> None:
    masked = mask_database_url("postgresql+psycopg://south_invest:secret-password@db:5432/south_invest")

    assert "secret-password" not in masked
    assert "***" in masked
    assert "south_invest" in masked


def test_database_engine_and_session_factory_use_sync_sqlalchemy() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    session_factory = create_session_factory(engine)

    assert isinstance(engine, Engine)
    assert session_factory.kw["autoflush"] is False
    assert session_factory.kw["expire_on_commit"] is False


def test_declarative_metadata_starts_empty_until_domain_models_are_added() -> None:
    assert Base.metadata.tables == {}
