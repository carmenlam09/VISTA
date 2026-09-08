from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.triage  # noqa: F401 — registers tables on Base.metadata
import app.services.triage_engine as triage_engine_module
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.entity_lookup import EntityLookupService
from app.services.module2_source import Module2Source
from app.services.module3_source import Module3Source
from app.services.reasoning_service import DeterministicReasoningService

NONEXISTENT_DB = Path("/nonexistent/for-api-tests.db")


@pytest.fixture(autouse=True)
def _force_fixture_sources(monkeypatch):
    """The route module uses the module-level `triage_engine` singleton —
    point its internals at fixture-backed sources so API tests are
    deterministic regardless of real Module 1/2/3 state on this machine."""
    monkeypatch.setattr(triage_engine_module.triage_engine, "_entity_lookup", EntityLookupService(db_path=str(NONEXISTENT_DB)))
    monkeypatch.setattr(triage_engine_module.triage_engine, "_module2_source", Module2Source(module2_db_path=str(NONEXISTENT_DB)))
    monkeypatch.setattr(
        triage_engine_module.triage_engine,
        "_module3_source",
        Module3Source(base_url="http://127.0.0.1:1", timeout_seconds=0.2),
    )
    monkeypatch.setattr(triage_engine_module.triage_engine, "_reasoner", DeterministicReasoningService())


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'api_test.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def test_triage_endpoint_returns_ranked_labeled_results(client):
    response = client.get("/api/entities/vendor:fixture-1/triage")
    assert response.status_code == 200
    body = response.json()

    assert body["entity_id"] == "vendor:fixture-1"
    assert len(body["results"]) == 3
    assert body["results"][0]["disposition_recommendation"] == "high_priority_review"
    for result in body["results"]:
        assert result["label"].startswith("AI-suggested")


def test_override_endpoint_records_a_reviewer_decision(client):
    triage_response = client.get("/api/entities/vendor:fixture-1/triage")
    triage_id = triage_response.json()["results"][0]["triage_id"]

    override_response = client.post(
        f"/api/entities/vendor:fixture-1/triage/{triage_id}/override",
        json={"reviewer_decision": "confirmed_true_hit", "reviewer_notes": "Confirmed against internal records."},
        headers={"X-User-Id": "reviewer-42", "X-User-Role": "reviewer"},
    )
    assert override_response.status_code == 200
    override_body = override_response.json()
    assert override_body["triage_id"] == triage_id
    assert override_body["actor_id"] == "reviewer-42"
    assert override_body["reviewer_decision"] == "confirmed_true_hit"

    overrides_list = client.get("/api/entities/vendor:fixture-1/triage/overrides")
    assert overrides_list.status_code == 200
    assert len(overrides_list.json()) == 1


def test_override_of_unknown_triage_id_returns_404(client):
    response = client.post(
        "/api/entities/vendor:fixture-1/triage/does-not-exist/override",
        json={"reviewer_decision": "confirmed_false_positive"},
    )
    assert response.status_code == 404


def test_a_second_triage_run_archives_the_first_batch_but_override_still_resolves(client):
    """Overrides must keep working even against a recommendation that a
    later run has superseded/archived — a reviewer must always be able to
    explain what they overrode."""
    first = client.get("/api/entities/vendor:fixture-1/triage")
    first_triage_id = first.json()["results"][0]["triage_id"]

    client.get("/api/entities/vendor:fixture-1/triage")  # second run archives the first batch

    override_response = client.post(
        f"/api/entities/vendor:fixture-1/triage/{first_triage_id}/override",
        json={"reviewer_decision": "confirmed_false_positive"},
    )
    assert override_response.status_code == 200


def test_clean_entity_triage_is_empty_but_valid(client):
    response = client.get("/api/entities/vendor:fixture-clean/triage")
    assert response.status_code == 200
    assert response.json()["results"] == []
