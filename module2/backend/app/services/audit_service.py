"""Audit logging. Every aggregation query and every result view is logged —
this is a banking control system; audit logging is a hard requirement."""

import uuid

from sqlalchemy.orm import Session

from app.core.auth import Actor
from app.models.screening import AuditLogRecord
from app.schemas.screening import SourceName


class AuditService:
    def log(
        self,
        db: Session,
        actor: Actor,
        action: str,
        entity_id: str,
        sources: list[SourceName] | None = None,
        detail: dict | None = None,
    ) -> None:
        db.add(
            AuditLogRecord(
                id=str(uuid.uuid4()),
                actor_id=actor.user_id,
                actor_role=actor.role.value,
                action=action,
                entity_id=entity_id,
                sources=[s.value for s in (sources or [])],
                detail=detail or {},
            )
        )
        db.commit()

    def list_for_entity(self, db: Session, entity_id: str) -> list[AuditLogRecord]:
        return (
            db.query(AuditLogRecord)
            .filter(AuditLogRecord.entity_id == entity_id)
            .order_by(AuditLogRecord.created_at.desc())
            .all()
        )


audit_service = AuditService()
