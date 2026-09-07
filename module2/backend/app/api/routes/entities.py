from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import Actor, get_current_actor
from app.core.config import settings
from app.db.session import get_db
from app.schemas.entity import EntityProfile
from app.schemas.screening import EntityScreeningStatus, SourceStatus, SourceStatusBadge
from app.services.aggregation_service import aggregation_service
from app.services.entity_service import entity_service

router = APIRouter(prefix="/api/entities", tags=["entities"])


def _status_for(entity: EntityProfile, db: Session) -> EntityScreeningStatus:
    cached = aggregation_service.get_cached(db, entity.entity_id)
    total_hits = sum(r.hit_count for r in cached)
    unavailable = [r for r in cached if r.status != SourceStatus.OK]
    last_queried_at = max((r.queried_at for r in cached), default=None)

    is_stale = last_queried_at is None or (
        (datetime.now(timezone.utc) - last_queried_at).total_seconds() > settings.screening_cache_ttl_seconds
    )

    if total_hits > 0:
        badge = SourceStatusBadge.HITS_FOUND
    elif unavailable and len(unavailable) == len(cached):
        badge = SourceStatusBadge.SOURCE_UNAVAILABLE
    elif not cached or is_stale:
        badge = SourceStatusBadge.NEEDS_REFRESH
    elif unavailable:
        badge = SourceStatusBadge.SOURCE_UNAVAILABLE
    else:
        badge = SourceStatusBadge.CLEAR

    return EntityScreeningStatus(
        entity_id=entity.entity_id,
        legal_name=entity.legal_name,
        entity_type=entity.entity_type.value,
        badge=badge,
        total_hits=total_hits,
        sources_queried=len(cached),
        sources_unavailable=len(unavailable),
        last_queried_at=last_queried_at,
    )


@router.get("", response_model=list[EntityScreeningStatus])
def list_entities(db: Session = Depends(get_db), actor: Actor = Depends(get_current_actor)):
    """Search/filter view: every screened entity with its status badge."""
    return [_status_for(e, db) for e in entity_service.list_entities()]


@router.get("/{entity_id}", response_model=EntityProfile)
def get_entity(entity_id: str, actor: Actor = Depends(get_current_actor)):
    entity = entity_service.get_entity(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")
    return entity
