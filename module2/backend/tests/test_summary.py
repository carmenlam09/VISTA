from app.services.aggregation_service import aggregation_service
from app.services.entity_service import entity_service
from app.services.summary_generator import DeterministicSummaryGenerator

generator = DeterministicSummaryGenerator()


async def test_summary_for_genuinely_risky_entity(db_session):
    entity = entity_service.get_entity("vendor:4")
    aggregation = await aggregation_service.aggregate(db_session, entity, force_refresh=True)

    summary = await generator.generate(entity, aggregation.results)

    assert summary.entity_id == entity.entity_id
    assert summary.narrative
    assert summary.findings
    assert summary.generator == "deterministic-fallback"

    valid_sources = {r.source for r in aggregation.results}
    for finding in summary.findings:
        assert finding.source in valid_sources  # every finding is attributed to a real, queried source


async def test_summary_for_clean_entity_has_no_findings(db_session):
    entity = entity_service.get_entity("vendor:9")
    aggregation = await aggregation_service.aggregate(db_session, entity, force_refresh=True)

    summary = await generator.generate(entity, aggregation.results)

    assert summary.findings == []
    assert "No adverse findings" in summary.narrative


async def test_summary_lists_failed_sources_as_missing(db_session):
    entity = entity_service.get_entity("vendor:1")
    aggregation = await aggregation_service.aggregate(db_session, entity, force_refresh=True)

    summary = await generator.generate(entity, aggregation.results)

    assert any("netreveal" in note for note in summary.missing_or_inconclusive)
