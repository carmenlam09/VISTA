from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import Actor, get_current_actor, require_admin
from app.db.session import get_db
from app.services.audit_service import audit_service

router = APIRouter(prefix="/api/entities/{entity_id}/audit", tags=["audit"])


@router.get("")
def list_audit_log(
    entity_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
):
    """Admin-only: raw audit trail for one entity (who queried/viewed what, when)."""
    require_admin(actor)
    records = audit_service.list_for_entity(db, entity_id)
    return [
        {
            "id": r.id,
            "actor_id": r.actor_id,
            "actor_role": r.actor_role,
            "action": r.action,
            "entity_id": r.entity_id,
            "sources": r.sources,
            "detail": r.detail,
            "created_at": r.created_at,
        }
        for r in records
    ]
