"""Persists every generated report version and every status transition —
matching Modules 2/4/5's audit_service.py pattern. Every generation event
and every status change is logged in the append-only `report_history` table,
in addition to the permanent, never-overwritten `generated_reports` row for
that version.
"""

import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.report import GeneratedReportRecord, ReportHistoryRecord
from app.schemas.report import GeneratedReport, ReportStatus


class AuditService:
    def next_version(self, db: Session, entity_id: str) -> int:
        latest = db.query(func.max(GeneratedReportRecord.version)).filter(GeneratedReportRecord.entity_id == entity_id).scalar()
        return (latest or 0) + 1

    def save_report(self, db: Session, report: GeneratedReport, actor_id: str) -> None:
        db.add(
            GeneratedReportRecord(
                id=report.report_id,
                entity_id=report.entity_id,
                version=report.version,
                status=report.status.value,
                file_path=report.file_path,
                narrative=report.narrative.model_dump(mode="json"),
                manifest=report.manifest.model_dump(mode="json"),
                missing_sections=report.missing_sections,
                generator=report.generator,
            )
        )
        db.add(
            ReportHistoryRecord(
                id=str(uuid.uuid4()),
                report_id=report.report_id,
                entity_id=report.entity_id,
                version=report.version,
                action="generated",
                actor_id=actor_id,
                details={"status": report.status.value, "missing_sections": report.missing_sections},
            )
        )
        db.commit()

    def get_latest_report(self, db: Session, entity_id: str) -> GeneratedReportRecord | None:
        return (
            db.query(GeneratedReportRecord)
            .filter(GeneratedReportRecord.entity_id == entity_id)
            .order_by(GeneratedReportRecord.version.desc())
            .first()
        )

    def get_report(self, db: Session, entity_id: str, version: int) -> GeneratedReportRecord | None:
        return (
            db.query(GeneratedReportRecord)
            .filter(GeneratedReportRecord.entity_id == entity_id, GeneratedReportRecord.version == version)
            .first()
        )

    def change_status(
        self, db: Session, record: GeneratedReportRecord, actor_id: str, new_status: ReportStatus, notes: str | None
    ) -> GeneratedReportRecord:
        old_status = record.status
        record.status = new_status.value
        db.add(
            ReportHistoryRecord(
                id=str(uuid.uuid4()),
                report_id=record.id,
                entity_id=record.entity_id,
                version=record.version,
                action="status_changed",
                actor_id=actor_id,
                details={"from": old_status, "to": new_status.value},
                notes=notes,
            )
        )
        db.commit()
        db.refresh(record)
        return record

    def list_history(self, db: Session, entity_id: str) -> list[ReportHistoryRecord]:
        return (
            db.query(ReportHistoryRecord)
            .filter(ReportHistoryRecord.entity_id == entity_id)
            .order_by(ReportHistoryRecord.created_at.desc())
            .all()
        )


audit_service = AuditService()
