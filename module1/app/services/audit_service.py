"""Audit logging (NEW capability — Module 1 had none before this refactor,
per the realignment spec's explicit instruction to bring it up to Module 2's
standard). Every extraction run and every save is logged permanently."""

import uuid

from sqlalchemy.orm import Session

from app.core.auth import Actor
from app.models.audit import AuditLogRecord


class AuditService:
    def log(self, db: Session, actor: Actor, action: str, vendor_id: int | None = None, detail: dict | None = None) -> None:
        db.add(
            AuditLogRecord(
                id=str(uuid.uuid4()),
                actor_id=actor.user_id,
                actor_role=actor.role.value,
                action=action,
                vendor_id=vendor_id,
                detail=detail or {},
            )
        )
        db.commit()

    def list_for_vendor(self, db: Session, vendor_id: int) -> list[AuditLogRecord]:
        return (
            db.query(AuditLogRecord)
            .filter(AuditLogRecord.vendor_id == vendor_id)
            .order_by(AuditLogRecord.created_at.desc())
            .all()
        )


audit_service = AuditService()
