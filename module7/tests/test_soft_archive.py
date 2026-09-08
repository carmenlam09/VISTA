"""Superseded and retention-aged-out ('archived') records must remain fully
retrievable for audit, but must not surface in normal day-to-day search
results unless explicitly requested."""

from app.schemas.ingestion import IngestionRequest
from app.schemas.retrieval import RetrievalQuery
from datetime import datetime, timedelta, timezone


def test_superseded_record_excluded_from_default_search(db_session, ingestion, retrieval):
    request = IngestionRequest(
        entity_id="vendor:archive-test",
        record_type="kyv_review",
        timestamp=datetime.now(timezone.utc),
        source_module="module2",
        source_reference="ref-archive-1",
        summary_text="Initial review.",
        tags=[],
        payload={"v": 1},
    )
    first = ingestion.ingest(db_session, request)
    ingestion.ingest(db_session, request.model_copy(update={"summary_text": "Corrected review.", "payload": {"v": 2}}))

    default_response = retrieval.search(db_session, RetrievalQuery(entity_id="vendor:archive-test"))
    assert len(default_response.results) == 1
    assert default_response.results[0].record.status == "active"

    with_superseded = retrieval.search(
        db_session, RetrievalQuery(entity_id="vendor:archive-test", include_superseded=True)
    )
    assert len(with_superseded.results) == 2
    statuses = {r.record.status for r in with_superseded.results}
    assert statuses == {"active", "superseded"}

    # the superseded record is STILL directly retrievable by id — never deleted
    assert ingestion.get_by_id(db_session, first.record.record_id) is not None


def test_retention_aged_record_excluded_from_default_search_but_still_retrievable(db_session, ingestion, retrieval):
    old_timestamp = datetime.now(timezone.utc) - timedelta(days=5000)  # well past every record_type's retain_days
    request = IngestionRequest(
        entity_id="vendor:old-record",
        record_type="adverse_news_assessment",
        timestamp=old_timestamp,
        source_module="module3",
        source_reference="ref-old-1",
        summary_text="A very old adverse media assessment.",
        tags=[],
        payload={},
    )
    created = ingestion.ingest(db_session, request)

    default_response = retrieval.search(db_session, RetrievalQuery(entity_id="vendor:old-record"))
    assert default_response.results == []

    archived_response = retrieval.search(db_session, RetrievalQuery(entity_id="vendor:old-record", include_archived=True))
    assert len(archived_response.results) == 1
    assert archived_response.results[0].is_archived is True
    assert archived_response.results[0].record.record_id == created.record.record_id


def test_recent_record_is_not_archived(db_session, ingestion, retrieval):
    request = IngestionRequest(
        entity_id="vendor:recent-record",
        record_type="kyv_review",
        timestamp=datetime.now(timezone.utc),
        source_module="module2",
        source_reference="ref-recent-1",
        summary_text="A recent review.",
        tags=[],
        payload={},
    )
    ingestion.ingest(db_session, request)

    response = retrieval.search(db_session, RetrievalQuery(entity_id="vendor:recent-record"))
    assert len(response.results) == 1
    assert response.results[0].is_archived is False
