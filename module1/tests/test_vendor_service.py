from app.schemas.vendor import Director, RelatedParty, Shareholder, Ubo, VendorProfile
from app.services.vendor_service import get_vendor, save_vendor, search_vendors


def _profile(**overrides) -> VendorProfile:
    defaults = dict(
        vendor_name="Meridian Supplies Sdn. Bhd.",
        registration_number="202001012345",
        country="Malaysia",
        address="Level 12, Menara Meridian, Kuala Lumpur, Malaysia",
        directors=[Director(director_name="Aisha Rahman", nationality="Malaysian", id_number="780512-08-5566")],
        shareholders=[Shareholder(shareholder_name="Meridian Holdings Berhad", ownership_percentage=60.0)],
        ubo=[Ubo(ubo_name="Aisha Rahman", ownership_percentage=40.0)],
        related_parties=[RelatedParty(related_party_name="Meridian Logistics Sdn. Bhd.", relationship_type="subsidiary")],
    )
    defaults.update(overrides)
    return VendorProfile(**defaults)


def test_save_and_get_round_trip(db_session):
    vendor_id = save_vendor(db_session, _profile())
    record = get_vendor(db_session, vendor_id)

    assert record is not None
    assert record.vendor_name == "Meridian Supplies Sdn. Bhd."
    assert len(record.directors) == 1
    assert record.directors[0].director_name == "Aisha Rahman"
    assert record.directors[0].id_number == "780512-08-5566"
    assert record.shareholders[0].ownership_percentage == 60.0
    assert record.related_parties[0].relationship_type == "subsidiary"


def test_blank_named_entries_are_not_persisted(db_session):
    profile = _profile(directors=[Director(director_name=""), Director(director_name="Real Director")])
    vendor_id = save_vendor(db_session, profile)
    record = get_vendor(db_session, vendor_id)
    assert [d.director_name for d in record.directors] == ["Real Director"]


def test_search_matches_name_or_registration_number(db_session):
    save_vendor(db_session, _profile(vendor_name="Alpha Trading", registration_number="111111"))
    save_vendor(db_session, _profile(vendor_name="Beta Holdings", registration_number="222222"))

    by_name = search_vendors(db_session, "Alpha")
    assert [v.vendor_name for v in by_name] == ["Alpha Trading"]

    by_reg = search_vendors(db_session, "222222")
    assert [v.vendor_name for v in by_reg] == ["Beta Holdings"]

    all_results = search_vendors(db_session, "")
    assert len(all_results) == 2


def test_search_orders_by_created_date_descending(db_session):
    """`created_date` is SQLite's CURRENT_TIMESTAMP, second-resolution only
    (unchanged from the pre-refactor implementation) — two inserts in the
    same second can tie, so this only asserts the query never puts an
    *older* row ahead of a newer one, not a strict tiebreak order."""
    first_id = save_vendor(db_session, _profile(vendor_name="First"))
    second_id = save_vendor(db_session, _profile(vendor_name="Second"))
    results = search_vendors(db_session, "")

    assert {r.vendor_id for r in results} == {first_id, second_id}
    dates = [r.created_date for r in results]
    assert dates == sorted(dates, reverse=True)


def test_unknown_vendor_returns_none(db_session):
    assert get_vendor(db_session, 999) is None
