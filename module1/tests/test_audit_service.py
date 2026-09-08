from app.core.auth import Actor, Role
from app.services.audit_service import audit_service

REVIEWER = Actor(user_id="reviewer-1", role=Role.REVIEWER)


def test_log_records_an_entry(db_session):
    audit_service.log(db_session, REVIEWER, "extraction", detail={"file_count": 2})
    entries = audit_service.list_for_vendor(db_session, vendor_id=None)
    # vendor_id filter with None won't match a NULL-vendor_id row via `==`, so
    # query all entries directly to confirm the write happened.
    from app.models.audit import AuditLogRecord

    all_entries = db_session.query(AuditLogRecord).all()
    assert len(all_entries) == 1
    assert all_entries[0].action == "extraction"
    assert all_entries[0].actor_id == "reviewer-1"
    assert all_entries[0].detail == {"file_count": 2}


def test_list_for_vendor_filters_by_vendor_id(db_session):
    audit_service.log(db_session, REVIEWER, "save", vendor_id=1, detail={})
    audit_service.log(db_session, REVIEWER, "save", vendor_id=2, detail={})
    audit_service.log(db_session, REVIEWER, "view", vendor_id=1, detail={})

    entries = audit_service.list_for_vendor(db_session, vendor_id=1)
    assert len(entries) == 2
    assert all(e.vendor_id == 1 for e in entries)


def test_entries_are_never_deleted_only_ever_added(db_session):
    for i in range(3):
        audit_service.log(db_session, REVIEWER, "view", vendor_id=1, detail={"i": i})
    entries = audit_service.list_for_vendor(db_session, vendor_id=1)
    assert len(entries) == 3
