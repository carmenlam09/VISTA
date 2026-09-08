from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import Actor, get_current_actor, require_authorized
from app.db.session import get_db
from app.schemas.assessment import RiskAssessmentDraft
from app.services.assessment_engine import assessment_engine
from app.services.audit_service import audit_service

router = APIRouter(prefix="/api/entities/{entity_id}/risk-assessment", tags=["risk-assessment"])


@router.get("", response_model=RiskAssessmentDraft)
async def get_risk_assessment(
    entity_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> RiskAssessmentDraft:
    """Risk assessment drafts are sensitive ('Confidential' in the source
    policy doc) — restricted to reviewer/approver/admin roles. Runs the
    full pipeline fresh on every call and persists the draft — per the
    spec, every draft is logged for audit, not just cached."""
    require_authorized(actor)

    draft = await assessment_engine.run_assessment(entity_id)
    if draft is None:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")

    audit_service.save_draft(db, draft, actor.user_id)
    return draft
