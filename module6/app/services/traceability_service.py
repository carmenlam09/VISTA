"""Builds the traceability manifest (capability 4): a separate,
machine-readable JSON mapping each narrative section's claims back to the
specific finding references, rule IDs, and source module records that
support them. Keeps the report itself readable prose — no inline citation
markers — while preserving full auditability underneath.

Every section_id that appears in the report's narrative gets at least one
manifest entry, even when the underlying data was missing (with an empty
`source_references` list) — so completeness can be verified mechanically:
no section is ever silently untraceable.
"""

from datetime import datetime, timezone

from app.schemas.report import TraceabilityEntry, TraceabilityManifest
from app.schemas.report_data import ReportData, SectionStatus


def build_manifest(entity_id: str, report_id: str, version: int, data: ReportData) -> TraceabilityManifest:
    entries: list[TraceabilityEntry] = []

    # --- executive_summary: composite across all upstream modules --------
    entries.append(
        TraceabilityEntry(section_id="executive_summary", claim="Entity identification", source_module="module1", source_references=[data.entity_id])
    )
    if data.risk_assessment.status == SectionStatus.OK:
        a = data.risk_assessment.assessment
        entries.append(
            TraceabilityEntry(
                section_id="executive_summary", claim=f"Overall risk rating: {a.overall_risk_rating}",
                source_module="module5", source_references=[a.draft_id],
            )
        )
    if data.screening_evidence.status == SectionStatus.OK:
        entries.append(
            TraceabilityEntry(
                section_id="executive_summary", claim=f"{len(data.screening_evidence.results)} screening source(s) summarized",
                source_module="module2", source_references=[r.result_id for r in data.screening_evidence.results],
            )
        )
    if data.adverse_media.status == SectionStatus.OK:
        entries.append(
            TraceabilityEntry(
                section_id="executive_summary", claim=f"{len(data.adverse_media.findings)} adverse media finding(s) summarized",
                source_module="module3", source_references=[f.finding_id for f in data.adverse_media.findings],
            )
        )
    if data.triage.status == SectionStatus.OK:
        entries.append(
            TraceabilityEntry(
                section_id="executive_summary", claim=f"{len(data.triage.results)} triaged finding(s) summarized",
                source_module="module4", source_references=[t.triage_id for t in data.triage.results],
            )
        )

    # --- screening_findings_summary ---------------------------------------
    if data.screening_evidence.status == SectionStatus.OK:
        for r in data.screening_evidence.results:
            entries.append(
                TraceabilityEntry(
                    section_id="screening_findings_summary", claim=f"{r.source}: {r.hit_count} hit(s), status {r.status}",
                    source_module="module2", source_references=[r.result_id],
                )
            )
    else:
        entries.append(
            TraceabilityEntry(section_id="screening_findings_summary", claim="No screening evidence available", source_module="module2", source_references=[])
        )

    # --- adverse_media_findings --------------------------------------------
    if data.adverse_media.status == SectionStatus.OK:
        for f in data.adverse_media.findings:
            entries.append(
                TraceabilityEntry(
                    section_id="adverse_media_findings", claim=f"{'/'.join(f.themes) or 'untitled theme'}: {f.source_hit.headline}",
                    source_module="module3", source_references=[f.finding_id],
                )
            )
    else:
        entries.append(
            TraceabilityEntry(section_id="adverse_media_findings", claim="No adverse media findings available", source_module="module3", source_references=[])
        )

    # --- triage_summary -----------------------------------------------------
    if data.triage.status == SectionStatus.OK:
        for t in data.triage.results:
            entries.append(
                TraceabilityEntry(
                    section_id="triage_summary", claim=f"{t.disposition_recommendation} (confidence {t.confidence_score})",
                    source_module="module4", source_references=[t.triage_id, t.finding_reference],
                )
            )
    else:
        entries.append(
            TraceabilityEntry(section_id="triage_summary", claim="No triage results available", source_module="module4", source_references=[])
        )

    # --- risk_assessment ------------------------------------------------------
    if data.risk_assessment.status == SectionStatus.OK:
        a = data.risk_assessment.assessment
        entries.append(
            TraceabilityEntry(
                section_id="risk_assessment", claim=f"Overall risk rating {a.overall_risk_rating}",
                source_module="module5", source_references=[a.draft_id],
            )
        )
        for rule in a.matched_rules:
            entries.append(
                TraceabilityEntry(
                    section_id="risk_assessment", claim=f"Matched rule {rule.rule_id}: {rule.contribution}",
                    source_module="module5", source_references=[rule.rule_id, *rule.triggering_finding_references],
                )
            )
    else:
        entries.append(
            TraceabilityEntry(section_id="risk_assessment", claim="No risk assessment available", source_module="module5", source_references=[])
        )

    # --- edd_recommendation ----------------------------------------------------
    if data.risk_assessment.status == SectionStatus.OK:
        a = data.risk_assessment.assessment
        entries.append(
            TraceabilityEntry(
                section_id="edd_recommendation", claim=f"EDD level {a.edd_recommendation.level}",
                source_module="module5", source_references=[a.draft_id],
            )
        )
    else:
        entries.append(
            TraceabilityEntry(section_id="edd_recommendation", claim="No EDD recommendation available", source_module="module5", source_references=[])
        )

    return TraceabilityManifest(entity_id=entity_id, report_id=report_id, version=version, entries=entries, generated_at=datetime.now(timezone.utc))
