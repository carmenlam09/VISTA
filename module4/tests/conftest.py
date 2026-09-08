from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.triage  # noqa: F401 — registers tables on Base.metadata
from app.db.base import Base
from app.services.entity_lookup import EntityLookupService
from app.services.module2_source import Module2Source
from app.services.module3_source import Module3Source
from app.services.triage_engine import TriageEngine
from app.services.reasoning_service import DeterministicReasoningService

NONEXISTENT_DB = Path("/nonexistent/for-tests.db")


@pytest.fixture()
def fixture_entity_lookup() -> EntityLookupService:
    """Deterministic regardless of whatever is in Module 1's real database
    on this machine — tests always use the bundled fixtures."""
    return EntityLookupService(db_path=str(NONEXISTENT_DB))


@pytest.fixture()
def fixture_module2_source() -> Module2Source:
    return Module2Source(module2_db_path=str(NONEXISTENT_DB))


@pytest.fixture()
def fixture_module3_source() -> Module3Source:
    """An unreachable base_url with a tiny timeout, so this always falls
    back to fixtures fast rather than depending on Module 3 actually
    running for tests to pass."""
    return Module3Source(base_url="http://127.0.0.1:1", timeout_seconds=0.2)


@pytest.fixture()
def fixture_triage_engine(fixture_entity_lookup, fixture_module2_source, fixture_module3_source) -> TriageEngine:
    return TriageEngine(
        entity_lookup=fixture_entity_lookup,
        m2_source=fixture_module2_source,
        m3_source=fixture_module3_source,
        reasoner=DeterministicReasoningService(),
    )


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
