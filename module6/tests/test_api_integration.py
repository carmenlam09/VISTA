from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.report  # noqa: F401 — registers tables on Base.metadata
import app.services.report_engine as report_engine_module
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.entity_lookup import EntityLookupService
from app.services.module2_source import Module2Source
from app.services.module3_source import Module3Source
from app.services.module4_source import Module4Source
from app.services.module5_source import Module5Source
from app.services.narrative_service import DeterministicNarrativeService
from app.services.report_data_aggregator import ReportDataAggregator

NONEXISTENT_DB = Path("/nonexistent/for-api-tests.db")


def _fixture_aggregator(fixtures_subdir: str) -> ReportDataAggregator:
    return ReportDataAggregator(
        entity_lookup=EntityLookupService(db_path=str(NONEXISTENT_DB), fixtures_subdir=fixtures_subdir),
        m2_source=Module2Source(module2_db_path=str(NONEXISTENT_DB), fixtures_subdir=fixtures_subdir),
        m3_source=Module3Source(base_url="http://127.0.0.1:1", timeout_seconds=0.2, fixtures_subdir=fixtures_subdir),
        m4_source=Module4Source(module4_db_path=str(NONEXISTENT_DB), fixtures_subdir=fixtures_subdir),
        m5_source=Module5Source(module5_db_path=str(NONEXISTENT_DB), fixtures_subdir=fixtures_subdir),
    )


@pytest.fixture(autouse=True)
def _force_fixture_sources(monkeypatch, tmp_path):
    """The route modules use the module-level `report_engine` singleton —
    point its internals at fixture-backed sources and a temp output dir so
    API tests are deterministic and don't write into the real
    generated_reports/ directory."""
    monkeypatch.setattr(report_engine_module.report_engine, "_aggregator", _fixture_aggregator("complete"))
    monkeypatch.setattr(report_engine_module.report_engine, "_narrator", DeterministicNarrativeService())
    monkeypatch.setattr(report_engine_module.report_engine, "_output_dir", tmp_path / "reports")


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


def test_get_report_generates_version_1_when_none_exists(client):
    response = client.get("/api/entities/vendor:report-complete/report")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 1
    assert body["status"] == "draft"
    assert body["label"].startswith("AI-drafted")


def test_get_report_twice_returns_the_same_version_no_duplicate_generation(client):
    first = client.get("/api/entities/vendor:report-complete/report").json()
    second = client.get("/api/entities/vendor:report-complete/report").json()
    assert first["report_id"] == second["report_id"]
    assert first["version"] == second["version"] == 1


def test_regenerate_always_creates_a_new_version(client):
    v1 = client.get("/api/entities/vendor:report-complete/report").json()
    v2 = client.post("/api/entities/vendor:report-complete/report/regenerate").json()
    v3 = client.post("/api/entities/vendor:report-complete/report/regenerate").json()

    assert [v1["version"], v2["version"], v3["version"]] == [1, 2, 3]
    assert len({v1["report_id"], v2["report_id"], v3["report_id"]}) == 3  # all distinct


def test_unknown_entity_returns_404(client):
    response = client.get("/api/entities/vendor:does-not-exist/report")
    assert response.status_code == 404


def test_download_returns_the_docx_file(client):
    report = client.get("/api/entities/vendor:report-complete/report").json()
    response = client.get(f"/api/entities/vendor:report-complete/report/{report['version']}/download")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats")


def test_manifest_endpoint_returns_the_traceability_manifest(client):
    report = client.get("/api/entities/vendor:report-complete/report").json()
    response = client.get(f"/api/entities/vendor:report-complete/report/{report['version']}/manifest")
    assert response.status_code == 200
    manifest = response.json()
    assert manifest["entity_id"] == "vendor:report-complete"
    assert len(manifest["entries"]) > 0


def test_reviewer_can_move_to_under_review_but_not_approve(client):
    report = client.get("/api/entities/vendor:report-complete/report").json()
    version = report["version"]

    under_review = client.post(
        f"/api/entities/vendor:report-complete/report/{version}/status",
        json={"status": "under_review"},
        headers={"X-User-Id": "reviewer-1", "X-User-Role": "reviewer"},
    )
    assert under_review.status_code == 200
    assert under_review.json()["status"] == "under_review"

    approve_attempt = client.post(
        f"/api/entities/vendor:report-complete/report/{version}/status",
        json={"status": "approved"},
        headers={"X-User-Id": "reviewer-1", "X-User-Role": "reviewer"},
    )
    assert approve_attempt.status_code == 403


def test_approver_can_approve(client):
    report = client.get("/api/entities/vendor:report-complete/report").json()
    version = report["version"]

    approve = client.post(
        f"/api/entities/vendor:report-complete/report/{version}/status",
        json={"status": "approved", "notes": "Reviewed and concur."},
        headers={"X-User-Id": "approver-1", "X-User-Role": "approver"},
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"


def test_history_logs_generation_and_status_changes(client):
    report = client.get("/api/entities/vendor:report-complete/report").json()
    client.post("/api/entities/vendor:report-complete/report/regenerate")
    client.post(
        f"/api/entities/vendor:report-complete/report/{report['version']}/status",
        json={"status": "under_review"},
    )

    history = client.get("/api/entities/vendor:report-complete/report/history").json()
    actions = [h["action"] for h in history]
    assert actions.count("generated") == 2
    assert actions.count("status_changed") == 1


def test_unrecognized_role_is_rejected(client):
    response = client.get(
        "/api/entities/vendor:report-complete/report", headers={"X-User-Role": "not-a-real-role"}
    )
    assert response.status_code == 400
