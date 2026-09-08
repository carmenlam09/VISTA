from datetime import datetime, timezone

from app.models.record import KnowledgeRecordORM
from app.schemas.ingestion import IngestionRequest
from app.schemas.record import RecordStatus


def _request(**overrides) -> IngestionRequest:
    defaults = dict(
        entity_id="vendor:x",
        record_type="kyv_review",
        timestamp=datetime.now(timezone.utc),
        source_module="module2",
        source_reference="ref-1",
        summary_text="Initial review, no findings.",
        tags=[],
        payload={"outcome": "clean"},
    )
    defaults.update(overrides)
    return IngestionRequest(**defaults)


def test_first_ingestion_creates_an_active_record(db_session, ingestion):
    result = ingestion.ingest(db_session, _request())
    assert result.was_duplicate is False
    assert result.record.status == RecordStatus.ACTIVE
    assert result.superseded_record_id is None


def test_resubmitting_identical_content_is_a_noop(db_session, ingestion):
    first = ingestion.ingest(db_session, _request())
    second = ingestion.ingest(db_session, _request())

    assert second.was_duplicate is True
    assert second.record.record_id == first.record.record_id

    # confirm nothing new was actually written
    all_records = db_session.query(KnowledgeRecordORM).all()
    assert len(all_records) == 1


def test_resubmitting_changed_content_supersedes_the_prior_version(db_session, ingestion):
    first = ingestion.ingest(db_session, _request())
    updated_request = _request(summary_text="Corrected review, one finding identified.", payload={"outcome": "flagged"})
    second = ingestion.ingest(db_session, updated_request)

    assert second.was_duplicate is False
    assert second.record.record_id != first.record.record_id
    assert second.superseded_record_id == first.record.record_id
    assert second.record.lineage_id == first.record.lineage_id
    assert second.record.status == RecordStatus.ACTIVE

    # the prior version is NEVER deleted — it's retrievable, just superseded
    old = ingestion.get_by_id(db_session, first.record.record_id)
    assert old is not None
    assert old.status == RecordStatus.SUPERSEDED


def test_different_source_reference_creates_a_separate_lineage(db_session, ingestion):
    first = ingestion.ingest(db_session, _request(source_reference="ref-1"))
    other = ingestion.ingest(db_session, _request(source_reference="ref-2"))

    assert first.record.lineage_id != other.record.lineage_id
    assert first.record.status == RecordStatus.ACTIVE
    assert other.record.status == RecordStatus.ACTIVE


def test_lineage_returns_every_version_oldest_first(db_session, ingestion):
    first = ingestion.ingest(db_session, _request())
    ingestion.ingest(db_session, _request(summary_text="Revision 2.", payload={"outcome": "revised"}))
    third = ingestion.ingest(db_session, _request(summary_text="Revision 3.", payload={"outcome": "final"}))

    lineage = ingestion.get_lineage(db_session, first.record.lineage_id)
    assert len(lineage) == 3
    assert [r.status for r in lineage] == [RecordStatus.SUPERSEDED, RecordStatus.SUPERSEDED, RecordStatus.ACTIVE]
    assert lineage[-1].record_id == third.record.record_id


def test_content_hash_changes_when_payload_changes(db_session, ingestion):
    first = ingestion.ingest(db_session, _request())
    second = ingestion.ingest(db_session, _request(payload={"outcome": "different"}))
    assert first.record.content_hash != second.record.content_hash


def test_unknown_record_id_returns_none(db_session, ingestion):
    assert ingestion.get_by_id(db_session, "does-not-exist") is None
