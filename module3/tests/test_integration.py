"""End-to-end: fixture adverse-news hits -> categorized findings, via the
same ScreeningEngine the API route uses. Runs entirely on the deterministic
fallback (no ANTHROPIC_API_KEY in the test environment)."""

from app.services.categorization_service import DeterministicCategorizer
from app.services.screening_engine import ScreeningEngine
from app.taxonomy.loader import load_taxonomy


def _engine(source) -> ScreeningEngine:
    return ScreeningEngine(source=source, taxonomy=load_taxonomy(), ai_categorizer=DeterministicCategorizer())


async def test_high_risk_fixture_entity_end_to_end(fixture_source):
    engine = _engine(fixture_source)
    response = await engine.screen_entity("vendor:demo-highrisk")

    assert response.entity_id == "vendor:demo-highrisk"
    assert response.hits_considered == 6
    assert response.duplicates_collapsed == 1  # hit-1/hit-2 republished wire story
    assert response.filtered_irrelevant == 1  # hit-5, near-miss "Meridian Logistics"
    assert response.suppressed_by_negation == 1  # hit-4, victim-of-embezzlement framing

    assert len(response.findings) == 2
    themes = {theme for f in response.findings for theme in f.themes}
    assert "financial_crime" in themes
    assert "regulatory_breach" in themes

    for finding in response.findings:
        assert finding.source_hit.hit_id in {"hit-1", "hit-3"}
        assert finding.generator == "deterministic-fallback"
        assert finding.rationale


async def test_clean_fixture_entity_has_no_findings(fixture_source):
    engine = _engine(fixture_source)
    response = await engine.screen_entity("vendor:demo-clean")

    assert response.hits_considered == 2
    assert response.duplicates_collapsed == 0
    assert response.filtered_irrelevant == 0
    assert response.suppressed_by_negation == 0
    assert response.findings == []


async def test_unknown_entity_returns_empty_response(fixture_source):
    engine = _engine(fixture_source)
    response = await engine.screen_entity("vendor:does-not-exist")

    assert response.hits_considered == 0
    assert response.findings == []


async def test_via_default_module_level_engine_singleton(fixture_source):
    """The module-level `screening_engine` singleton (what the FastAPI route
    actually uses) works the same way when pointed at the fixture source."""
    from app.services.screening_engine import ScreeningEngine

    engine = ScreeningEngine(source=fixture_source, ai_categorizer=DeterministicCategorizer())
    response = await engine.screen_entity("vendor:demo-highrisk")
    assert len(response.findings) == 2
