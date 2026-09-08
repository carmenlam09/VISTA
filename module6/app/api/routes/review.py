from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.routes._shared import record_to_report
from app.core.auth import Actor, get_current_actor, require_approval_role, require_authorized
from app.core.time import ensure_utc
from app.db.session import get_db
from app.schemas.report import GeneratedReport, ReportHistoryEntry, ReportStatus, ReportStatusChangeRequest
from app.services.audit_service import audit_service

router = APIRouter(prefix="/api/entities/{entity_id}/report", tags=["report"])


@router.post("/{version}/status", response_model=GeneratedReport)
def change_status(
    entity_id: str,
    version: int,
    request: ReportStatusChangeRequest,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> GeneratedReport:
    """Moves a report through draft -> under_review -> approved. Approving
    (the Checker step, mirroring Module 5) requires approver/admin; moving
    to under_review only requires an authorized role."""
    if request.status == ReportStatus.APPROVED:
        require_approval_role(actor)
    else:
        require_authorized(actor)

    record = audit_service.get_report(db, entity_id, version)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Report version {version} not found for entity '{entity_id}'")

    updated = audit_service.change_status(db, record, actor.user_id, request.status, request.notes)
    return record_to_report(updated)


@router.get("/history", response_model=list[ReportHistoryEntry])
def get_history(
    entity_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> list[ReportHistoryEntry]:
    require_authorized(actor)
    records = audit_service.list_history(db, entity_id)
    return [
        ReportHistoryEntry(
            history_id=r.id,
            report_id=r.report_id,
            entity_id=r.entity_id,
            version=r.version,
            action=r.action,
            actor_id=r.actor_id,
            details=r.details,
            notes=r.notes,
            created_at=ensure_utc(r.created_at),
        )
        for r in records
    ]
