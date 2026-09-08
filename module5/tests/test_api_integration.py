from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.assessment  # noqa: F401 — registers tables on Base.metadata
import app.services.assessment_engine as assessment_engine_module
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.entity_lookup import EntityLookupService
from app.services.narrative_service import DeterministicNarrativeService
from app.services.theme_enrichment import ThemeEnrichmentService
from app.services.triage_source import TriageSource

NONEXISTENT_DB = Path("/nonexistent/for-api-tests.db")


@pytest.fixture(autouse=True)
def _force_fixture_sources(monkeypatch):
    """The route module uses the module-level `assessment_engine` singleton
    — point its internals at fixture-backed sources so API tests are
    deterministic regardless of real Module 1/2/3/4 state on this machine."""
    monkeypatch.setattr(assessment_engine_module.assessment_engine, "_entity_lookup", EntityLookupService(db_path=str(NONEXISTENT_DB)))
    monkeypatch.setattr(assessment_engine_module.assessment_engine, "_triage_source", TriageSource(module4_db_path=str(NONEXISTENT_DB)))
    monkeypatch.setattr(
        assessment_engine_module.assessment_engine,
        "_theme_enricher",
        ThemeEnrichmentService(module2_db_path=str(NONEXISTENT_DB), module3_base_url="http://127.0.0.1:1", module3_timeout_seconds=0.2),
    )
    monkeypatch.setattr(assessment_engine_module.assessment_engine, "_narrator", DeterministicNarrativeService())


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


def test_get_draft_returns_labeled_ai_drafted_assessment(client):
    response = client.get("/api/entities/vendor:fixture-overlap/risk-assessment")
    assert response.status_code == 200
    body = response.json()
    assert body["draft_status"] == "ai_drafted"
    assert body["overall_risk_rating"] == "high"
    assert body["label"].startswith("AI-drafted")


def test_unknown_entity_returns_404(client):
    response = client.get("/api/entities/vendor:does-not-exist/risk-assessment")
    assert response.status_code == 404


def test_unrecognized_role_is_rejected(client):
    response = client.get(
        "/api/entities/vendor:fixture-overlap/risk-assessment", headers={"X-User-Role": "not-a-real-role"}
    )
    assert response.status_code == 400


def test_reviewer_can_edit_but_not_approve(client):
    draft = client.get("/api/entities/vendor:fixture-excluded/risk-assessment").json()
    draft_id = draft["draft_id"]

    edit_response = client.post(
        f"/api/entities/vendor:fixture-excluded/risk-assessment/{draft_id}/edit",
        json={"overall_risk_rating": "high", "edit_notes": "Escalating based on additional context."},
        headers={"X-User-Id": "reviewer-1", "X-User-Role": "reviewer"},
    )
    assert edit_response.status_code == 200
    assert edit_response.json()["overall_risk_rating"] == "high"
    assert edit_response.json()["draft_status"] == "reviewer_edited"

    approve_response = client.post(
        f"/api/entities/vendor:fixture-excluded/risk-assessment/{draft_id}/approve",
        json={},
        headers={"X-User-Id": "reviewer-1", "X-User-Role": "reviewer"},
    )
    assert approve_response.status_code == 403


def test_approver_can_approve(client):
    draft = client.get("/api/entities/vendor:fixture-excluded/risk-assessment").json()
    draft_id = draft["draft_id"]

    approve_response = client.post(
        f"/api/entities/vendor:fixture-excluded/risk-assessment/{draft_id}/approve",
        json={"approval_notes": "Reviewed and concur."},
        headers={"X-User-Id": "approver-1", "X-User-Role": "approver"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["draft_status"] == "approved"


def test_full_lifecycle_is_logged_in_history(client):
    draft = client.get("/api/entities/vendor:fixture-excluded/risk-assessment").json()
    draft_id = draft["draft_id"]

    client.post(
        f"/api/entities/vendor:fixture-excluded/risk-assessment/{draft_id}/edit",
        json={"materiality_justification": "Reviewer-adjusted narrative."},
        headers={"X-User-Id": "reviewer-1", "X-User-Role": "reviewer"},
    )
    client.post(
        f"/api/entities/vendor:fixture-excluded/risk-assessment/{draft_id}/approve",
        json={},
        headers={"X-User-Id": "approver-1", "X-User-Role": "approver"},
    )

    history = client.get("/api/entities/vendor:fixture-excluded/risk-assessment/history").json()
    actions = [h["action"] for h in history]
    assert actions.count("drafted") == 1
    assert actions.count("edited") == 1
    assert actions.count("approved") == 1


def test_edit_of_unknown_draft_returns_404(client):
    response = client.post(
        "/api/entities/vendor:fixture-overlap/risk-assessment/does-not-exist/edit",
        json={"overall_risk_rating": "high"},
    )
    assert response.status_code == 404


def test_a_second_draft_run_archives_the_first_but_edit_still_resolves(client):
    """Edits must keep working even against a draft a later run has
    superseded/archived — a reviewer must always be able to explain what
    they changed."""
    first = client.get("/api/entities/vendor:fixture-overlap/risk-assessment").json()
    first_draft_id = first["draft_id"]

    client.get("/api/entities/vendor:fixture-overlap/risk-assessment")  # second run archives the first

    edit_response = client.post(
        f"/api/entities/vendor:fixture-overlap/risk-assessment/{first_draft_id}/edit",
        json={"edit_notes": "Note on the superseded draft."},
    )
    assert edit_response.status_code == 200
