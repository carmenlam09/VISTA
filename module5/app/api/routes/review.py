from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import Actor, get_current_actor, require_approval_role, require_authorized
from app.core.time import ensure_utc
from app.db.session import get_db
from app.models.assessment import RiskAssessmentDraftRecord
from app.schemas.assessment import DraftApprovalRequest, DraftEditRequest, DraftHistoryEntry, RiskAssessmentDraft
from app.services.audit_service import audit_service

router = APIRouter(prefix="/api/entities/{entity_id}/risk-assessment", tags=["risk-assessment"])


def _record_to_draft(record: RiskAssessmentDraftRecord) -> RiskAssessmentDraft:
    return RiskAssessmentDraft(
        draft_id=record.id,
        entity_id=record.entity_id,
        draft_status=record.draft_status,
        overall_risk_rating=record.overall_risk_rating,
        matched_rules=record.matched_rules,
        materiality_justification=record.materiality_justification,
        edd_recommendation={"level": record.edd_level, "required_steps": record.edd_required_steps},
        contributing_findings=record.contributing_findings,
        excluded_findings=record.excluded_findings,
        generator=record.generator,
        created_at=ensure_utc(record.created_at),
    )


def _get_draft_or_404(db: Session, entity_id: str, draft_id: str) -> RiskAssessmentDraftRecord:
    record = audit_service.get_draft(db, draft_id)
    if record is None or record.entity_id != entity_id:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found for entity '{entity_id}'")
    return record


@router.post("/{draft_id}/edit", response_model=RiskAssessmentDraft)
def edit_draft(
    entity_id: str,
    draft_id: str,
    request: DraftEditRequest,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> RiskAssessmentDraft:
    """A reviewer's edit to a draft's conclusions — logged regardless of
    whether the draft has since been superseded by a newer AI-drafted run."""
    require_authorized(actor)
    record = _get_draft_or_404(db, entity_id, draft_id)
    updated = audit_service.apply_edit(db, record, actor.user_id, request)
    return _record_to_draft(updated)


@router.post("/{draft_id}/approve", response_model=RiskAssessmentDraft)
def approve_draft(
    entity_id: str,
    draft_id: str,
    request: DraftApprovalRequest,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> RiskAssessmentDraft:
    """The Checker step — requires the approver or admin role, so a
    reviewer cannot self-approve their own draft (role-based only; this
    does not verify the approver is a different person from whoever last
    edited it — see module5/README.md Assumptions)."""
    require_approval_role(actor)
    record = _get_draft_or_404(db, entity_id, draft_id)
    updated = audit_service.approve(db, record, actor.user_id, request)
    return _record_to_draft(updated)


@router.get("/history", response_model=list[DraftHistoryEntry])
def get_draft_history(
    entity_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> list[DraftHistoryEntry]:
    require_authorized(actor)
    records = audit_service.list_history(db, entity_id)
    return [
        DraftHistoryEntry(
            history_id=r.id,
            draft_id=r.draft_id,
            entity_id=r.entity_id,
            action=r.action,
            actor_id=r.actor_id,
            changes=r.changes,
            notes=r.notes,
            created_at=ensure_utc(r.created_at),
        )
        for r in records
    ]
