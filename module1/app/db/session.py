from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

_NEW_NULLABLE_COLUMNS = {
    "directors": [("id_number", "TEXT")],
    "shareholders": [("id_number", "TEXT")],
    "ubos": [("id_number", "TEXT")],
}


def _upgrade_existing_tables() -> None:
    """The real vista.db already exists with the pre-refactor schema (no
    `id_number` columns). `Base.metadata.create_all()` only creates missing
    TABLES, not missing COLUMNS on tables that already exist, so upgrade it
    explicitly and idempotently — safe to run on every startup, and safe on
    a brand-new database too (the columns are already there from
    `create_all`, so this becomes a no-op)."""
    with engine.connect() as connection:
        for table, columns in _NEW_NULLABLE_COLUMNS.items():
            existing = {row[1] for row in connection.execute(text(f"PRAGMA table_info({table})"))}
            for column, sql_type in columns:
                if column not in existing:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))
        connection.commit()


def init_db() -> None:
    if settings.database_url.startswith("sqlite:///"):
        db_path = Path(settings.database_url.replace("sqlite:///", "", 1))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    import app.models.audit  # noqa: F401 — registers tables on Base.metadata
    import app.models.vendor  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _upgrade_existing_tables()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
