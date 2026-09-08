from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.triage import TriageRunResponse
from app.services.audit_service import audit_service
from app.services.triage_engine import triage_engine

router = APIRouter(prefix="/api/entities/{entity_id}/triage", tags=["triage"])


@router.get("", response_model=TriageRunResponse)
async def get_triage(entity_id: str, db: Session = Depends(get_db)) -> TriageRunResponse:
    """Runs the full pipeline fresh on every call and persists the batch —
    per the spec, every triage recommendation is logged for audit, not just
    cached. Ranked so high_priority_review surfaces first; likely_false_
    positive items stay in the list, never hidden."""
    results = await triage_engine.run_triage(entity_id)
    audit_service.save_triage_batch(db, entity_id, results)
    return TriageRunResponse(entity_id=entity_id, results=results, generated_at=datetime.now(timezone.utc))
