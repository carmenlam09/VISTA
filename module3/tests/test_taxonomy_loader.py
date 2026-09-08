import pytest

from app.schemas.taxonomy import RiskTheme
from app.taxonomy.loader import TaxonomyLoadError, load_taxonomy


def test_loads_starter_taxonomy():
    taxonomy = load_taxonomy()
    assert taxonomy.version
    assert len(taxonomy.keywords) > 0
    assert set(taxonomy.themes) == set(RiskTheme)


def test_every_keyword_maps_to_a_known_theme():
    taxonomy = load_taxonomy()
    for entry in taxonomy.keywords:
        assert entry.themes
        for theme in entry.themes:
            assert theme in RiskTheme


def test_missing_file_raises_load_error(tmp_path):
    with pytest.raises(TaxonomyLoadError):
        load_taxonomy(tmp_path / "does-not-exist.yaml")


def test_invalid_yaml_raises_load_error(tmp_path):
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("keywords: [unclosed", encoding="utf-8")
    with pytest.raises(TaxonomyLoadError):
        load_taxonomy(bad_file)


def test_keyword_with_unknown_theme_fails_validation(tmp_path):
    bad_file = tmp_path / "bad_theme.yaml"
    bad_file.write_text(
        """
version: "1.0"
themes:
  financial_crime: "x"
  sanctions: "x"
  fraud: "x"
  regulatory_breach: "x"
  tax_offence: "x"
  esg: "x"
  operational: "x"
keywords:
  - phrase: "something"
    themes: [not_a_real_theme]
""",
        encoding="utf-8",
    )
    with pytest.raises(TaxonomyLoadError):
        load_taxonomy(bad_file)


def test_taxonomy_missing_a_theme_description_fails_validation(tmp_path):
    bad_file = tmp_path / "missing_theme.yaml"
    bad_file.write_text(
        """
version: "1.0"
themes:
  financial_crime: "x"
keywords: []
""",
        encoding="utf-8",
    )
    with pytest.raises(TaxonomyLoadError):
        load_taxonomy(bad_file)


def test_keyword_with_blank_phrase_fails_validation(tmp_path):
    bad_file = tmp_path / "blank_phrase.yaml"
    bad_file.write_text(
        """
version: "1.0"
themes:
  financial_crime: "x"
  sanctions: "x"
  fraud: "x"
  regulatory_breach: "x"
  tax_offence: "x"
  esg: "x"
  operational: "x"
keywords:
  - phrase: "   "
    themes: [fraud]
""",
        encoding="utf-8",
    )
    with pytest.raises(TaxonomyLoadError):
        load_taxonomy(bad_file)
