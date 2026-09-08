"""THE contract-regression test (Phase B, required as a permanent addition
to the suite, not a one-off script). Re-runs the exact same fixtures used to
capture fixtures/contract_baseline.json — BEFORE any refactor code was
touched — through the refactored pipeline, and asserts the persisted,
re-read shape (what Module 2, and transitively Modules 3-7, actually
consume) matches exactly, except for the explicitly documented, approved
changes below.

Fixtures run in the same order against one fresh database, so autoincrement
ids line up exactly with the baseline (vendor_id 1/2/3, director_id
1/2/3/4, ...) — this is what makes an exact equality comparison possible
without normalizing ids away.
"""

import copy
import json
from pathlib import Path

from app.services.entity_extractor import extract_entities
from app.services.pdf_service import extract_pdf_text
from app.services.vendor_profile_builder import build_vendor_profile
from app.services.vendor_service import get_vendor, save_vendor

TESTS_DIR = Path(__file__).resolve().parent
MODULE_DIR = TESTS_DIR.parent
REPO_ROOT = MODULE_DIR.parent
BASELINE_PATH = MODULE_DIR / "fixtures" / "contract_baseline.json"

FIXTURE_SOURCES = {
    "sample_vendor_txt": lambda: (MODULE_DIR / "fixtures" / "sample_vendor.txt").read_text(encoding="utf-8"),
    "ssm_sample_pdf": lambda: extract_pdf_text((REPO_ROOT / "SSM_sample.pdf").read_bytes()),
    "ssm_unmasked_report_pdf": lambda: extract_pdf_text((REPO_ROOT / "SSM_Unmasked_Report.pdf").read_bytes()),
}

# Every intentional difference from the pre-refactor baseline, and nothing
# else — see module1/README.md "Alignment refactor". If this test fails on
# a field NOT listed here, that's unapproved contract drift.
INTENTIONAL_VALUE_CHANGES = {
    "ssm_sample_pdf": {
        # Fix: shareholder name no longer leaks an unrelated repeated page-header
        # line when the corporate suffix wraps across two PDF lines.
        ("shareholders", 0, "shareholder_name"): "PUNCAK SEMANGAT TECHNOLOGY SDN. BHD.",
    },
}

# Fields that exist in the new output but not the old baseline (additive —
# see app/schemas/vendor.py), or that are inherently time-dependent and so
# can never equal a value captured at a different time. Both are excluded
# from the strict equality check; existence/type is still asserted directly.
FIELDS_EXCLUDED_FROM_BASELINE_DIFF = {"id_number", "created_date"}


def _strip_excluded_fields(value):
    if isinstance(value, dict):
        return {k: _strip_excluded_fields(v) for k, v in value.items() if k not in FIELDS_EXCLUDED_FROM_BASELINE_DIFF}
    if isinstance(value, list):
        return [_strip_excluded_fields(v) for v in value]
    return value


def _apply_intentional_changes(baseline_section: dict, changes: dict) -> dict:
    result = copy.deepcopy(baseline_section)
    for path, new_value in changes.items():
        node = result
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = new_value
    return result


def test_persisted_contract_matches_pre_refactor_baseline_except_documented_changes(db_session):
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    for fixture_name, get_text in FIXTURE_SOURCES.items():
        extraction = extract_entities(get_text())
        profile = build_vendor_profile([extraction])
        vendor_id = save_vendor(db_session, profile)
        record = get_vendor(db_session, vendor_id)
        assert record is not None

        actual = _strip_excluded_fields(record.model_dump(mode="json"))
        expected = _strip_excluded_fields(
            _apply_intentional_changes(baseline[fixture_name]["persisted_and_reread"], INTENTIONAL_VALUE_CHANGES.get(fixture_name, {}))
        )

        assert actual == expected, f"Unexpected contract drift for fixture '{fixture_name}'"

        # created_date is excluded from the value diff (it's a fresh timestamp every
        # run) but its presence/shape is still a real part of the contract.
        assert record.created_date  # non-empty string, e.g. "2026-09-08 12:44:56"


def test_ssm_sample_director_id_number_is_a_documented_new_capability(db_session):
    """The one new field this refactor adds to the persisted contract,
    asserted directly (it's excluded from the baseline diff above, so it
    needs its own assertion) — see Phase A gap #2."""
    extraction = extract_entities(extract_pdf_text((REPO_ROOT / "SSM_sample.pdf").read_bytes()))
    profile = build_vendor_profile([extraction])
    vendor_id = save_vendor(db_session, profile)
    record = get_vendor(db_session, vendor_id)

    assert record.directors[0].director_name == "SHERIZA BIN ZAKARIA"
    assert record.directors[0].id_number == "740210-06-5229"
