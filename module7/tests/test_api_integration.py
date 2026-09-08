from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.record  # noqa: F401 — registers tables on Base.metadata
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.fixture_loader import load_fixture_requests
from app.services.ingestion_service import ingestion_service


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


def _sample_request_payload() -> dict:
    request = load_fixture_requests()[0]
    return request.model_dump(mode="json")


def test_ingestion_requires_admin_role(client):
    response = client.post(
        "/api/knowledge-records", json=_sample_request_payload(), headers={"X-User-Role": "reviewer"}
    )
    assert response.status_code == 403


def test_admin_can_ingest_and_reviewer_can_retrieve(client):
    ingest_response = client.post(
        "/api/knowledge-records", json=_sample_request_payload(), headers={"X-User-Role": "admin"}
    )
    assert ingest_response.status_code == 200
    body = ingest_response.json()
    assert body["was_duplicate"] is False
    record_id = body["record"]["record_id"]

    get_response = client.get(f"/api/knowledge-records/{record_id}", headers={"X-User-Role": "reviewer"})
    assert get_response.status_code == 200
    assert get_response.json()["record_id"] == record_id


def test_reingesting_the_same_payload_is_idempotent_via_the_api(client):
    payload = _sample_request_payload()
    first = client.post("/api/knowledge-records", json=payload, headers={"X-User-Role": "admin"})
    second = client.post("/api/knowledge-records", json=payload, headers={"X-User-Role": "admin"})

    assert second.json()["was_duplicate"] is True
    assert second.json()["record"]["record_id"] == first.json()["record"]["record_id"]


def test_search_requires_authorized_role(client):
    response = client.post(
        "/api/knowledge-records/search", json={}, headers={"X-User-Role": "not-a-real-role"}
    )
    assert response.status_code == 400


def test_end_to_end_ingest_then_retrieve(client):
    for request in load_fixture_requests():
        response = client.post("/api/knowledge-records", json=request.model_dump(mode="json"), headers={"X-User-Role": "admin"})
        assert response.status_code == 200

    search_response = client.post(
        "/api/knowledge-records/search",
        json={"query_text": "name collision false positive sanctions watchlist"},
        headers={"X-User-Role": "reviewer"},
    )
    assert search_response.status_code == 200
    results = search_response.json()["results"]
    assert results
    assert results[0]["record"]["entity_id"] == "director:knowledge-1"
    assert "disclaimer" in search_response.json()


def test_lineage_endpoint_returns_full_history(client):
    payload = _sample_request_payload()
    first = client.post("/api/knowledge-records", json=payload, headers={"X-User-Role": "admin"}).json()

    updated = dict(payload)
    updated["summary_text"] = "Updated assessment."
    updated["payload"] = {"note": "revised"}
    client.post("/api/knowledge-records", json=updated, headers={"X-User-Role": "admin"})

    lineage_response = client.get(
        f"/api/knowledge-records/lineage/{first['record']['lineage_id']}", headers={"X-User-Role": "reviewer"}
    )
    assert lineage_response.status_code == 200
    lineage = lineage_response.json()
    assert len(lineage) == 2
    assert [r["status"] for r in lineage] == ["superseded", "active"]


def test_unknown_record_id_returns_404(client):
    response = client.get("/api/knowledge-records/does-not-exist", headers={"X-User-Role": "reviewer"})
    assert response.status_code == 404
