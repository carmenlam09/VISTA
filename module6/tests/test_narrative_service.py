from app.services.narrative_service import DeterministicNarrativeService

narrator = DeterministicNarrativeService()


async def test_complete_data_produces_all_five_sections(complete_aggregator):
    data = await complete_aggregator.aggregate("vendor:report-complete")
    narrative = await narrator.generate(data.entity.profile, data)

    for section in narrative.sections():
        assert section.text
        assert section.generator


async def test_risk_assessment_narrative_reuses_module5_text_verbatim(complete_aggregator):
    data = await complete_aggregator.aggregate("vendor:report-complete")
    narrative = await narrator.generate(data.entity.profile, data)

    assert data.risk_assessment.assessment.materiality_justification in narrative.risk_assessment_narrative.text
    assert narrative.risk_assessment_narrative.generator.startswith("module5-reuse:")


async def test_missing_sections_are_explicitly_stated_not_blank(incomplete_aggregator):
    data = await incomplete_aggregator.aggregate("vendor:report-incomplete")
    narrative = await narrator.generate(data.entity.profile, data)

    assert "No Module 2" in narrative.screening_findings_summary.text
    assert "No Module 3" in narrative.adverse_media_narrative.text
    assert "No Module 5" in narrative.risk_assessment_narrative.text
    assert "No Module 5" in narrative.edd_recommendation_writeup.text
    # the executive summary is composite prose, not a single missing-note passthrough,
    # but it must still be non-empty and must not fabricate figures for absent data
    assert narrative.executive_summary.text
    assert "0 hit" not in narrative.executive_summary.text  # no invented counts


async def test_screening_summary_reports_a_source_level_error(complete_aggregator):
    data = await complete_aggregator.aggregate("vendor:report-complete")
    narrative = await narrator.generate(data.entity.profile, data)
    assert "unavailable" in narrative.screening_findings_summary.text
    assert "Registry service timed out" in narrative.screening_findings_summary.text
