from app.services.traceability_service import build_manifest

ALL_SECTION_IDS = {
    "executive_summary",
    "screening_findings_summary",
    "adverse_media_findings",
    "triage_summary",
    "risk_assessment",
    "edd_recommendation",
}


async def test_every_narrative_section_has_at_least_one_manifest_entry(complete_aggregator):
    data = await complete_aggregator.aggregate("vendor:report-complete")
    manifest = build_manifest(data.entity_id, "report-1", 1, data)

    section_ids_present = {e.section_id for e in manifest.entries}
    assert ALL_SECTION_IDS <= section_ids_present


async def test_every_entry_with_ok_data_carries_nonempty_source_references(complete_aggregator):
    data = await complete_aggregator.aggregate("vendor:report-complete")
    manifest = build_manifest(data.entity_id, "report-1", 1, data)

    # entries whose claim doesn't start with "No " (the missing-data phrasing) should cite something
    for entry in manifest.entries:
        if not entry.claim.startswith("No "):
            assert entry.source_references, f"entry {entry.claim!r} has no source references"


async def test_incomplete_data_still_produces_a_complete_manifest_with_empty_references(incomplete_aggregator):
    """A missing section must still appear in the manifest — with an empty
    reference list, not be omitted from the manifest entirely."""
    data = await incomplete_aggregator.aggregate("vendor:report-incomplete")
    manifest = build_manifest(data.entity_id, "report-1", 1, data)

    section_ids_present = {e.section_id for e in manifest.entries}
    assert ALL_SECTION_IDS <= section_ids_present

    missing_sections = {"screening_findings_summary", "adverse_media_findings", "triage_summary", "risk_assessment", "edd_recommendation"}
    for entry in manifest.entries:
        if entry.section_id in missing_sections:
            assert entry.source_references == []


async def test_matched_rule_citations_include_rule_id_and_triggering_findings(complete_aggregator):
    data = await complete_aggregator.aggregate("vendor:report-complete")
    manifest = build_manifest(data.entity_id, "report-1", 1, data)

    rule_entries = [e for e in manifest.entries if e.section_id == "risk_assessment" and "Matched rule" in e.claim]
    assert len(rule_entries) == 2
    for entry in rule_entries:
        assert entry.source_module == "module5"
        assert len(entry.source_references) >= 2  # rule_id + at least one triggering finding reference


async def test_manifest_carries_correct_entity_report_and_version(complete_aggregator):
    data = await complete_aggregator.aggregate("vendor:report-complete")
    manifest = build_manifest(data.entity_id, "report-xyz", 3, data)

    assert manifest.entity_id == "vendor:report-complete"
    assert manifest.report_id == "report-xyz"
    assert manifest.version == 3
