from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import Actor, get_current_actor
from app.db.session import get_db
from app.schemas.entity import EntityProfile
from app.schemas.screening import AggregationResponse, ScreeningResult, SourceName
from app.services.aggregation_service import aggregation_service
from app.services.audit_service import audit_service
from app.services.entity_service import entity_service

router = APIRouter(prefix="/api/entities/{entity_id}/screening", tags=["screening"])


def _get_entity_or_404(entity_id: str) -> EntityProfile:
    entity = entity_service.get_entity(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")
    return entity


@router.get("", response_model=list[ScreeningResult])
def get_cached_results(
    entity_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
):
    """Fetch the latest cached result per source, without querying anything."""
    entity = _get_entity_or_404(entity_id)
    results = aggregation_service.get_cached(db, entity.entity_id)
    audit_service.log(db, actor, action="view", entity_id=entity.entity_id, sources=[r.source for r in results])
    return results


@router.post("/query", response_model=AggregationResponse)
async def trigger_aggregation(
    entity_id: str,
    sources: list[SourceName] | None = Query(default=None),
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
):
    """Query all (or the given) sources, serving fresh sources from cache."""
    entity = _get_entity_or_404(entity_id)
    response = await aggregation_service.aggregate(db, entity, sources=sources, force_refresh=False)
    audit_service.log(db, actor, action="query", entity_id=entity.entity_id, sources=response.requested_sources)
    return response


@router.post("/refresh", response_model=AggregationResponse)
async def force_refresh(
    entity_id: str,
    sources: list[SourceName] | None = Query(default=None),
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
):
    """Manual 'refresh this source' action — bypasses the cache entirely."""
    entity = _get_entity_or_404(entity_id)
    response = await aggregation_service.aggregate(db, entity, sources=sources, force_refresh=True)
    audit_service.log(db, actor, action="refresh", entity_id=entity.entity_id, sources=response.requested_sources)
    return response
