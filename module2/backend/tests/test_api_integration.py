import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.screening  # noqa: F401 — registers tables on Base.metadata
from app.db.base import Base
from app.db.session import get_db
from app.main import app


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


def test_entity_id_to_aggregation_to_summary_end_to_end(client):
    """The Definition-of-Done flow: entity_id -> aggregated results -> AI summary."""
    entities = client.get("/api/entities").json()
    assert any(e["entity_id"] == "vendor:4" for e in entities)

    entity = client.get("/api/entities/vendor:4")
    assert entity.status_code == 200
    assert entity.json()["legal_name"]

    aggregation = client.post("/api/entities/vendor:4/screening/query")
    assert aggregation.status_code == 200
    body = aggregation.json()
    assert len(body["results"]) == 5
    assert body["succeeded_sources"]

    cached = client.get("/api/entities/vendor:4/screening")
    assert cached.status_code == 200
    assert len(cached.json()) == 5

    summary = client.get("/api/entities/vendor:4/summary")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["entity_id"] == "vendor:4"
    assert summary_body["narrative"]
    assert summary_body["findings"]
    valid_sources = {r["source"] for r in body["results"]}
    for finding in summary_body["findings"]:
        assert finding["source"] in valid_sources


def test_entity_list_survives_after_a_source_has_been_queried(client):
    """Regression test: SQLite drops tzinfo on datetimes it returns, so once
    an entity has at least one cached ScreeningResult, computing staleness
    for the list-view badge must not crash comparing aware vs. naive
    datetimes (this only reproduces once `last_queried_at` is non-None)."""
    client.post("/api/entities/vendor:4/screening/query")

    response = client.get("/api/entities")
    assert response.status_code == 200
    statuses = {e["entity_id"]: e for e in response.json()}
    assert statuses["vendor:4"]["badge"] == "hits_found"
    assert statuses["vendor:4"]["last_queried_at"] is not None


def test_clean_entity_end_to_end(client):
    aggregation = client.post("/api/entities/vendor:9/screening/query")
    assert aggregation.status_code == 200

    summary = client.get("/api/entities/vendor:9/summary")
    assert summary.status_code == 200
    assert summary.json()["findings"] == []


def test_unknown_entity_returns_404(client):
    response = client.get("/api/entities/vendor:does-not-exist")
    assert response.status_code == 404


def test_audit_log_requires_admin_role(client):
    client.post("/api/entities/vendor:4/screening/query")

    reviewer_response = client.get(
        "/api/entities/vendor:4/audit", headers={"X-User-Role": "reviewer"}
    )
    assert reviewer_response.status_code == 403

    admin_response = client.get(
        "/api/entities/vendor:4/audit", headers={"X-User-Role": "admin", "X-User-Id": "admin-1"}
    )
    assert admin_response.status_code == 200
    assert len(admin_response.json()) >= 1
