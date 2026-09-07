from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import Actor, get_current_actor
from app.db.session import get_db
from app.schemas.summary import ScreeningSummary
from app.services.aggregation_service import aggregation_service
from app.services.audit_service import audit_service
from app.services.entity_service import entity_service
from app.services.summary_generator import summary_generator

router = APIRouter(prefix="/api/entities/{entity_id}/summary", tags=["summary"])


@router.get("", response_model=ScreeningSummary)
async def get_summary(
    entity_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
):
    entity = entity_service.get_entity(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")

    results = aggregation_service.get_cached(db, entity.entity_id)
    if not results:
        aggregation_response = await aggregation_service.aggregate(db, entity)
        results = aggregation_response.results

    summary = await summary_generator.generate(entity, results)
    audit_service.log(db, actor, action="view", entity_id=entity.entity_id, detail={"resource": "summary"})
    return summary
