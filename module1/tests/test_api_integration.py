from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.audit  # noqa: F401 — registers tables on Base.metadata
import app.models.vendor  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import app

FIXTURE_TXT = Path(__file__).resolve().parent.parent / "fixtures" / "sample_vendor.txt"


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


def test_extract_endpoint_returns_a_draft_profile(client):
    with open(FIXTURE_TXT, "rb") as f:
        response = client.post("/api/vendors/extract", files={"files": ("sample_vendor.txt", f, "text/plain")})
    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["vendor_name"] == "Meridian Supplies Sdn. Bhd."
    assert body["has_warnings"] is False


def test_full_extract_save_search_get_flow(client):
    with open(FIXTURE_TXT, "rb") as f:
        extract_response = client.post("/api/vendors/extract", files={"files": ("sample_vendor.txt", f, "text/plain")})
    profile = extract_response.json()["profile"]

    save_response = client.post("/api/vendors", json=profile)
    assert save_response.status_code == 200
    vendor_id = save_response.json()["vendor_id"]

    search_response = client.get("/api/vendors", params={"query": "Meridian"})
    assert search_response.status_code == 200
    assert any(v["vendor_id"] == vendor_id for v in search_response.json())

    get_response = client.get(f"/api/vendors/{vendor_id}")
    assert get_response.status_code == 200
    assert get_response.json()["vendor_name"] == "Meridian Supplies Sdn. Bhd."


def test_save_without_vendor_name_is_rejected(client):
    response = client.post(
        "/api/vendors",
        json={"vendor_name": "", "registration_number": "", "country": "", "address": "", "directors": [], "shareholders": [], "ubo": [], "related_parties": []},
    )
    assert response.status_code == 400


def test_unknown_vendor_returns_404(client):
    response = client.get("/api/vendors/999")
    assert response.status_code == 404


def test_unrecognized_role_is_rejected(client):
    response = client.get("/api/vendors", headers={"X-User-Role": "not-a-real-role"})
    assert response.status_code == 400


def test_health_and_root(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/", follow_redirects=False).status_code == 307
