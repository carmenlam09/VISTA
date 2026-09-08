from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.assessment  # noqa: F401 — registers tables on Base.metadata
from app.db.base import Base
from app.policy.loader import load_policy
from app.services.assessment_engine import AssessmentEngine
from app.services.entity_lookup import EntityLookupService
from app.services.narrative_service import DeterministicNarrativeService
from app.services.theme_enrichment import ThemeEnrichmentService
from app.services.triage_source import TriageSource

NONEXISTENT_DB = Path("/nonexistent/for-tests.db")


@pytest.fixture()
def fixture_entity_lookup() -> EntityLookupService:
    return EntityLookupService(db_path=str(NONEXISTENT_DB))


@pytest.fixture()
def fixture_triage_source() -> TriageSource:
    return TriageSource(module4_db_path=str(NONEXISTENT_DB))


@pytest.fixture()
def fixture_theme_enrichment() -> ThemeEnrichmentService:
    """An unreachable Module 3 base_url with a tiny timeout, so theme
    lookups for module3-sourced findings fall back to fixtures fast rather
    than depending on Module 3 actually running for tests to pass."""
    return ThemeEnrichmentService(module2_db_path=str(NONEXISTENT_DB), module3_base_url="http://127.0.0.1:1", module3_timeout_seconds=0.2)


@pytest.fixture()
def fixture_assessment_engine(fixture_entity_lookup, fixture_triage_source, fixture_theme_enrichment) -> AssessmentEngine:
    return AssessmentEngine(
        entity_lookup=fixture_entity_lookup,
        triage_src=fixture_triage_source,
        theme_enricher=fixture_theme_enrichment,
        policy=load_policy(),
        narrator=DeterministicNarrativeService(),
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
