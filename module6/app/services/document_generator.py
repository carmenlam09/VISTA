"""Populates the report template (capability 3) with ReportData + the
drafted narrative, producing a .docx file. Follows the template's declared
section order/types — see config/report_template.yaml — rather than
inventing a different structure. Swapping in the bank's real template means
replacing that YAML and, if its section shapes genuinely differ from the
`SectionType` values handled here, extending this file's per-type
rendering; the aggregation/narrative/traceability layers don't change.
"""

from pathlib import Path

from docx import Document

from app.schemas.report import ReportNarrative
from app.schemas.report_data import ReportData, SectionStatus
from app.schemas.report_template import ReportTemplateConfig, SectionType

TABLE_STYLE = "Light Grid Accent 1"


def generate_document(
    template: ReportTemplateConfig,
    data: ReportData,
    narrative: ReportNarrative,
    report_id: str,
    version: int,
    status: str,
    output_path: Path,
) -> None:
    doc = Document()
    doc.add_heading(template.title, level=0)

    if template.is_placeholder:
        warning = doc.add_paragraph()
        run = warning.add_run(
            "PLACEHOLDER TEMPLATE — not the bank's approved KYV report format. "
            "Do not use for real decisions until the real template is substituted."
        )
        run.bold = True

    narrative_by_id = {section.section_id: section for section in narrative.sections()}

    for section in template.sections:
        doc.add_heading(section.title, level=1)

        if section.type == SectionType.METADATA:
            _render_metadata(doc, section.section_id, data, report_id, version, status)
        elif section.type == SectionType.NARRATIVE:
            doc.add_paragraph(_narrative_text(narrative_by_id, section.section_id))
        elif section.type == SectionType.STRUCTURED:
            _render_entity_profile(doc, data)
        elif section.type == SectionType.NARRATIVE_PLUS_TABLE:
            doc.add_paragraph(_narrative_text(narrative_by_id, section.section_id))
            if section.section_id == "screening_findings_summary":
                _render_screening_table(doc, data)
            elif section.section_id == "adverse_media_findings":
                _render_adverse_media_table(doc, data)
        elif section.type == SectionType.TABLE:
            if section.section_id == "triage_summary":
                _render_triage_table(doc, data)
        elif section.type == SectionType.NARRATIVE_PLUS_LIST:
            doc.add_paragraph(_narrative_text(narrative_by_id, section.section_id))
            _render_edd_steps(doc, data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))


def _narrative_text(narrative_by_id: dict, section_id: str) -> str:
    section = narrative_by_id.get(section_id)
    return section.text if section else "(no narrative available for this section)"


def _render_metadata(doc: Document, section_id: str, data: ReportData, report_id: str, version: int, status: str) -> None:
    if section_id == "report_header":
        name = data.entity.profile.legal_name if data.entity.profile else data.entity_id
        doc.add_paragraph(f"Entity: {name} ({data.entity_id})")
        doc.add_paragraph(f"Report ID: {report_id}    Version: {version}    Status: {status}")
        doc.add_paragraph(f"Generated: {data.aggregated_at.isoformat()}")
        label = doc.add_paragraph()
        run = label.add_run("AI-drafted KYV report — pending reviewer sign-off, not final or approved.")
        run.italic = True
    elif section_id == "sign_off":
        doc.add_paragraph("Reviewer: ______________________    Date: ______________")
        doc.add_paragraph("Approver: ______________________    Date: ______________")


def _render_entity_profile(doc: Document, data: ReportData) -> None:
    if data.entity.status != SectionStatus.OK or data.entity.profile is None:
        doc.add_paragraph(data.entity.note or "No entity profile available.")
        return
    profile = data.entity.profile
    doc.add_paragraph(f"Legal name: {profile.legal_name}")
    doc.add_paragraph(f"Entity type: {profile.entity_type.value}")
    if profile.aliases:
        doc.add_paragraph(f"Aliases: {', '.join(profile.aliases)}")
    if profile.nationality:
        doc.add_paragraph(f"Nationality/jurisdiction: {profile.nationality}")
    for id_number in profile.id_numbers:
        doc.add_paragraph(f"{id_number.type}: {id_number.value}")
    if profile.related_entities:
        doc.add_paragraph("Related entities:")
        for rel in profile.related_entities:
            doc.add_paragraph(f"{rel.relationship}: {rel.entity_id}", style="List Bullet")


def _render_screening_table(doc: Document, data: ReportData) -> None:
    if data.screening_evidence.status != SectionStatus.OK:
        doc.add_paragraph(data.screening_evidence.note or "No screening evidence available.")
        return
    table = doc.add_table(rows=1, cols=3)
    table.style = TABLE_STYLE
    header = table.rows[0].cells
    header[0].text, header[1].text, header[2].text = "Source", "Status", "Hit Count"
    for result in data.screening_evidence.results:
        row = table.add_row().cells
        row[0].text, row[1].text, row[2].text = result.source, result.status, str(result.hit_count)


def _render_adverse_media_table(doc: Document, data: ReportData) -> None:
    if data.adverse_media.status != SectionStatus.OK:
        doc.add_paragraph(data.adverse_media.note or "No adverse media findings available.")
        return
    table = doc.add_table(rows=1, cols=3)
    table.style = TABLE_STYLE
    header = table.rows[0].cells
    header[0].text, header[1].text, header[2].text = "Headline", "Theme(s)", "Severity"
    for finding in data.adverse_media.findings:
        row = table.add_row().cells
        row[0].text = finding.source_hit.headline
        row[1].text = ", ".join(finding.themes)
        row[2].text = finding.severity


def _render_triage_table(doc: Document, data: ReportData) -> None:
    if data.triage.status != SectionStatus.OK:
        doc.add_paragraph(data.triage.note or "No triage results available.")
        return
    table = doc.add_table(rows=1, cols=3)
    table.style = TABLE_STYLE
    header = table.rows[0].cells
    header[0].text, header[1].text, header[2].text = "Finding", "Disposition", "Confidence"
    for result in data.triage.results:
        row = table.add_row().cells
        row[0].text = result.finding_summary.headline
        row[1].text = result.disposition_recommendation
        row[2].text = str(result.confidence_score)


def _render_edd_steps(doc: Document, data: ReportData) -> None:
    if data.risk_assessment.status != SectionStatus.OK:
        doc.add_paragraph(data.risk_assessment.note or "No EDD steps available.")
        return
    steps = data.risk_assessment.assessment.edd_recommendation.required_steps
    if not steps:
        doc.add_paragraph("No additional EDD steps specified.")
        return
    for step in steps:
        doc.add_paragraph(step, style="List Bullet")
