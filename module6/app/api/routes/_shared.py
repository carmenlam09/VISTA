from app.core.time import ensure_utc
from app.models.report import GeneratedReportRecord
from app.schemas.report import GeneratedReport


def record_to_report(record: GeneratedReportRecord) -> GeneratedReport:
    return GeneratedReport(
        report_id=record.id,
        entity_id=record.entity_id,
        version=record.version,
        status=record.status,
        file_path=record.file_path,
        narrative=record.narrative,
        manifest=record.manifest,
        missing_sections=record.missing_sections,
        generator=record.generator,
        created_at=ensure_utc(record.created_at),
    )
