from __future__ import annotations

import os

from sqlalchemy.engine import URL, make_url

DEFAULT_DATABASE_URL = "postgresql+psycopg://south_invest:south_invest_dev@127.0.0.1:5432/south_invest"


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def mask_database_url(database_url: str) -> str:
    return make_url(database_url).render_as_string(hide_password=True)


def database_name(database_url: str | None = None) -> str | None:
    url: URL = make_url(database_url or get_database_url())
    return url.database
