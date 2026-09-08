from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import Actor, get_current_actor
from app.db.session import get_db
from app.schemas.triage import OverrideRecord, OverrideRequest
from app.services.audit_service import audit_service

router = APIRouter(prefix="/api/entities/{entity_id}/triage", tags=["triage-overrides"])


@router.post("/{triage_id}/override", response_model=OverrideRecord)
def override_triage_result(
    entity_id: str,
    triage_id: str,
    request: OverrideRequest,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> OverrideRecord:
    """A reviewer confirming or overriding a recommendation. Logged
    permanently — including when it overrides an already-archived (i.e.
    superseded by a later run) recommendation — since override history is
    valuable input for Module 7 later."""
    record = audit_service.get_triage_record(db, triage_id)
    if record is None or record.entity_id != entity_id:
        raise HTTPException(
            status_code=404, detail=f"Triage result '{triage_id}' not found for entity '{entity_id}'"
        )
    override = audit_service.save_override(db, actor.user_id, record, request)
    return OverrideRecord(
        override_id=override.id,
        triage_id=override.triage_id,
        entity_id=override.entity_id,
        finding_reference=override.finding_reference,
        original_recommendation=override.original_recommendation,
        original_confidence_score=override.original_confidence_score,
        reviewer_decision=override.reviewer_decision,
        reviewer_notes=override.reviewer_notes,
        actor_id=override.actor_id,
        created_at=override.created_at,
    )


@router.get("/overrides", response_model=list[OverrideRecord])
def list_overrides(entity_id: str, db: Session = Depends(get_db)) -> list[OverrideRecord]:
    records = audit_service.list_overrides_for_entity(db, entity_id)
    return [
        OverrideRecord(
            override_id=r.id,
            triage_id=r.triage_id,
            entity_id=r.entity_id,
            finding_reference=r.finding_reference,
            original_recommendation=r.original_recommendation,
            original_confidence_score=r.original_confidence_score,
            reviewer_decision=r.reviewer_decision,
            reviewer_notes=r.reviewer_notes,
            actor_id=r.actor_id,
            created_at=r.created_at,
        )
        for r in records
    ]
