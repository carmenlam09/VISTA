from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.screening  # noqa: F401 — registers tables on Base.metadata
import app.services.entity_service as entity_service_module
from app.db.base import Base

NONEXISTENT_MODULE1_DB = Path("/nonexistent/module1-for-tests.db")


@pytest.fixture(autouse=True)
def _force_fixture_entities(monkeypatch):
    """Module 2's tests must be deterministic regardless of whatever data
    happens to be in Module 1's real SQLite database on this machine, so
    every test runs against the bundled fixture entities instead."""
    monkeypatch.setattr(entity_service_module.entity_service, "_db_path", NONEXISTENT_MODULE1_DB)


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
