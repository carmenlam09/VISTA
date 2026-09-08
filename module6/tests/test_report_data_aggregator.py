from app.schemas.report_data import SectionStatus


async def test_complete_fixture_set_has_all_sections_ok(complete_aggregator):
    data = await complete_aggregator.aggregate("vendor:report-complete")

    assert data.entity.status == SectionStatus.OK
    assert data.screening_evidence.status == SectionStatus.OK
    assert data.adverse_media.status == SectionStatus.OK
    assert data.triage.status == SectionStatus.OK
    assert data.risk_assessment.status == SectionStatus.OK

    assert len(data.screening_evidence.results) == 3
    assert len(data.adverse_media.findings) == 1
    assert len(data.triage.results) == 2
    assert data.risk_assessment.assessment.overall_risk_rating == "high"


async def test_incomplete_fixture_set_flags_every_missing_section(incomplete_aggregator):
    data = await incomplete_aggregator.aggregate("vendor:report-incomplete")

    assert data.entity.status == SectionStatus.OK  # the entity itself IS known
    assert data.screening_evidence.status == SectionStatus.MISSING
    assert data.screening_evidence.note
    assert data.adverse_media.status == SectionStatus.MISSING
    assert data.adverse_media.note
    assert data.triage.status == SectionStatus.MISSING
    assert data.triage.note
    assert data.risk_assessment.status == SectionStatus.MISSING
    assert data.risk_assessment.note


async def test_unknown_entity_returns_none(complete_aggregator):
    data = await complete_aggregator.aggregate("vendor:does-not-exist")
    assert data is None


async def test_a_source_level_error_is_preserved_not_hidden(complete_aggregator):
    """The fixture's public_records row has status='error' — this is
    different from the section being entirely missing, and must survive
    into ReportData so the report can say *why* that source is unavailable,
    not just that it has zero hits."""
    data = await complete_aggregator.aggregate("vendor:report-complete")
    public_records = next(r for r in data.screening_evidence.results if r.source == "public_records")
    assert public_records.status == "error"
    assert public_records.error_message == "Registry service timed out"
