from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.report  # noqa: F401 — registers tables on Base.metadata
from app.db.base import Base
from app.services.entity_lookup import EntityLookupService
from app.services.module2_source import Module2Source
from app.services.module3_source import Module3Source
from app.services.module4_source import Module4Source
from app.services.module5_source import Module5Source
from app.services.narrative_service import DeterministicNarrativeService
from app.services.report_data_aggregator import ReportDataAggregator
from app.services.report_engine import ReportEngine

NONEXISTENT_DB = Path("/nonexistent/for-tests.db")
UNREACHABLE_MODULE3_URL = "http://127.0.0.1:1"


def _make_aggregator(fixtures_subdir: str) -> ReportDataAggregator:
    return ReportDataAggregator(
        entity_lookup=EntityLookupService(db_path=str(NONEXISTENT_DB), fixtures_subdir=fixtures_subdir),
        m2_source=Module2Source(module2_db_path=str(NONEXISTENT_DB), fixtures_subdir=fixtures_subdir),
        m3_source=Module3Source(base_url=UNREACHABLE_MODULE3_URL, timeout_seconds=0.2, fixtures_subdir=fixtures_subdir),
        m4_source=Module4Source(module4_db_path=str(NONEXISTENT_DB), fixtures_subdir=fixtures_subdir),
        m5_source=Module5Source(module5_db_path=str(NONEXISTENT_DB), fixtures_subdir=fixtures_subdir),
    )


@pytest.fixture()
def complete_aggregator() -> ReportDataAggregator:
    return _make_aggregator("complete")


@pytest.fixture()
def incomplete_aggregator() -> ReportDataAggregator:
    return _make_aggregator("incomplete")


@pytest.fixture()
def complete_report_engine(tmp_path) -> ReportEngine:
    return ReportEngine(
        aggregator=_make_aggregator("complete"),
        narrator=DeterministicNarrativeService(),
        output_dir=str(tmp_path / "reports"),
    )


@pytest.fixture()
def incomplete_report_engine(tmp_path) -> ReportEngine:
    return ReportEngine(
        aggregator=_make_aggregator("incomplete"),
        narrator=DeterministicNarrativeService(),
        output_dir=str(tmp_path / "reports"),
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
