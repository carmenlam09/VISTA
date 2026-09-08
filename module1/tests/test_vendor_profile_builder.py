from app.services.vendor_profile_builder import build_vendor_profile


def test_merges_fields_from_multiple_extractions_first_non_empty_wins():
    extractions = [
        {"vendor_name": "", "registration_number": "12345", "country": "", "address": ""},
        {"vendor_name": "Example Corp", "registration_number": "99999", "country": "Malaysia", "address": "KL"},
    ]
    profile = build_vendor_profile(extractions)
    assert profile.vendor_name == "Example Corp"
    assert profile.registration_number == "12345"  # first extraction's non-empty value wins
    assert profile.country == "Malaysia"


def test_deduplicates_directors_by_normalized_name():
    extractions = [
        {"directors": [{"director_name": "Aisha Rahman", "nationality": "Malaysian"}]},
        {"directors": [{"director_name": "AISHA  RAHMAN", "nationality": ""}]},  # same person, different casing/spacing
        {"directors": [{"director_name": "Daniel Tan", "nationality": "Malaysian"}]},
    ]
    profile = build_vendor_profile(extractions)
    names = [d.director_name for d in profile.directors]
    assert names == ["Aisha Rahman", "Daniel Tan"]


def test_blank_names_are_dropped():
    extractions = [{"directors": [{"director_name": "", "nationality": "Malaysian"}, {"director_name": "Real Name"}]}]
    profile = build_vendor_profile(extractions)
    assert [d.director_name for d in profile.directors] == ["Real Name"]


def test_id_number_survives_the_build_step():
    extractions = [{"directors": [{"director_name": "Sheriza Bin Zakaria", "id_number": "740210-06-5229"}]}]
    profile = build_vendor_profile(extractions)
    assert profile.directors[0].id_number == "740210-06-5229"


def test_transient_shares_field_is_not_carried_into_the_built_profile():
    """Documented, intentional behavior — see vendor_profile_builder.py's
    module docstring. `shares` was never part of the persisted contract."""
    extractions = [{"shareholders": [{"shareholder_name": "Example Sdn Bhd", "ownership_percentage": None, "shares": 1000000.0}]}]
    profile = build_vendor_profile(extractions)
    dumped = profile.shareholders[0].model_dump()
    assert "shares" not in dumped


def test_empty_extractions_produce_an_empty_profile():
    profile = build_vendor_profile([])
    assert profile.vendor_name == ""
    assert profile.directors == []
