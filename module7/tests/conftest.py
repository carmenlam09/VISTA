import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.record  # noqa: F401 — registers tables on Base.metadata
from app.db.base import Base
from app.policy.loader import load_retention_policy
from app.services.fixture_loader import seed_fixture_history
from app.services.ingestion_service import IngestionService
from app.services.retrieval_service import RetrievalService


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


@pytest.fixture()
def ingestion() -> IngestionService:
    return IngestionService()


@pytest.fixture()
def retrieval() -> RetrievalService:
    return RetrievalService(policy=load_retention_policy())


@pytest.fixture()
def seeded_db(db_session, ingestion):
    """A db_session pre-loaded with the bundled fixture history."""
    seed_fixture_history(db_session, ingestion)
    return db_session
