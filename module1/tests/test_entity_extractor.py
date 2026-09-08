"""Unit tests for the deterministic local extractor, including the two
verified fixes made during the Module 1 alignment refactor (see
module1/README.md "Alignment refactor" and app/services/entity_extractor.py's
module docstring)."""

from pathlib import Path

import pytest

from app.services.entity_extractor import mock_extract
from app.services.pdf_service import extract_pdf_text

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SSM_SAMPLE_PDF = REPO_ROOT / "SSM_sample.pdf"
SSM_UNMASKED_PDF = REPO_ROOT / "SSM_Unmasked_Report.pdf"


def _pdf_text(path: Path) -> str:
    if not path.exists():
        pytest.skip(f"{path.name} not present in this checkout")
    return extract_pdf_text(path.read_bytes())


# --- Generic (non-SSM) plain-text extraction -----------------------------


def test_generic_extraction_from_labeled_text():
    text = (
        "Vendor Name: Meridian Supplies Sdn. Bhd.\n"
        "Registration Number: 202001012345\n"
        "Country: Malaysia\n"
        "Address: Level 12, Menara Meridian, Kuala Lumpur, Malaysia\n"
        "Directors: Aisha Rahman (Malaysian); Daniel Tan (Malaysian)\n"
        "Shareholders: Meridian Holdings Berhad (60%); Aisha Rahman (40%)\n"
        "UBO: Aisha Rahman (40%)\n"
        "Related Parties: Meridian Logistics Sdn. Bhd. (subsidiary)\n"
    )
    result = mock_extract(text)
    assert result["vendor_name"] == "Meridian Supplies Sdn. Bhd."
    assert result["registration_number"] == "202001012345"
    assert [d["director_name"] for d in result["directors"]] == ["Aisha Rahman (Malaysian)", "Daniel Tan (Malaysian)"]
    assert result["shareholders"][0]["ownership_percentage"] == 60.0


# --- SSM extraction: director ID-number capture (fix #2) -----------------


def test_ssm_director_id_number_is_captured_when_inline_pattern_matches():
    """Verified against the real SSM_sample.pdf text: the director line is
    'SHERIZA BIN ZAKARIA 740210-06-5229 DIRECTOR 07-03-2019', which the
    inline regex captures directly — previously the ID number was discarded
    even though it was right there in the text."""
    text = _pdf_text(SSM_SAMPLE_PDF)
    result = mock_extract(text)
    assert len(result["directors"]) == 1
    director = result["directors"][0]
    assert director["director_name"] == "SHERIZA BIN ZAKARIA"
    assert director["id_number"] == "740210-06-5229"


def test_ssm_secretary_is_still_excluded_from_directors():
    text = _pdf_text(SSM_SAMPLE_PDF)
    result = mock_extract(text)
    names = [d["director_name"] for d in result["directors"]]
    assert "ZALINA BINTI KASANI" not in names  # SECRETARY, not DIRECTOR


# --- SSM extraction: shareholder name-wrap bug fix (fix #1) --------------


def test_ssm_shareholder_name_recovers_wrapped_corporate_suffix():
    """SSM_sample.pdf's shareholder row wraps 'SDN.' / 'BHD.' across two
    PDF lines. Before the fix, this made the parser fall back to matching an
    unrelated repeated page-header line ('Nama : BIG DATAWORKS SDN. BHD.')
    as the shareholder name — a real, verified bug found while capturing the
    pre-refactor contract baseline."""
    text = _pdf_text(SSM_SAMPLE_PDF)
    result = mock_extract(text)
    assert len(result["shareholders"]) == 1
    shareholder_name = result["shareholders"][0]["shareholder_name"]
    assert shareholder_name == "PUNCAK SEMANGAT TECHNOLOGY SDN. BHD."
    assert "Nama" not in shareholder_name  # the bug's signature: header text leaking in


def test_ssm_shareholder_name_unaffected_when_not_wrapped():
    """SSM_Unmasked_Report.pdf's shareholder row does NOT wrap across
    lines, so this path was never buggy — confirm the fix doesn't change
    already-correct behavior."""
    text = _pdf_text(SSM_UNMASKED_PDF)
    result = mock_extract(text)
    assert len(result["shareholders"]) == 1
    assert result["shareholders"][0]["shareholder_name"] == "PUNCAK SEMANGAT TECHNOLOGY SDN. BHD."


def test_ssm_vendor_fields_extracted():
    text = _pdf_text(SSM_SAMPLE_PDF)
    result = mock_extract(text)
    assert result["vendor_name"] == "BIG DATAWORKS SDN. BHD."
    assert result["registration_number"] == "201101006232(934369-T)"
    assert result["country"] == "MALAYSIA"
