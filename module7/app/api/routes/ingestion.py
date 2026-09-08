from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import Actor, get_current_actor, require_admin, require_authorized
from app.db.session import get_db
from app.schemas.ingestion import IngestionRequest, IngestionResult
from app.schemas.record import KnowledgeRecord
from app.services.ingestion_service import ingestion_service

router = APIRouter(prefix="/api/knowledge-records", tags=["knowledge-records"])


@router.post("", response_model=IngestionResult)
def ingest_record(
    request: IngestionRequest,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> IngestionResult:
    """Meant to be called by Modules 1-6's backends (or a future
    integration pass), not directly by a human reviewer — admin-only,
    mirroring a system/service credential rather than a normal user role."""
    require_admin(actor)
    return ingestion_service.ingest(db, request)


@router.get("/{record_id}", response_model=KnowledgeRecord)
def get_record(
    record_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> KnowledgeRecord:
    require_authorized(actor)
    record = ingestion_service.get_by_id(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Knowledge record '{record_id}' not found")
    return record


@router.get("/lineage/{lineage_id}", response_model=list[KnowledgeRecord])
def get_lineage(
    lineage_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> list[KnowledgeRecord]:
    """Every version of the same underlying record, oldest first — the
    full audit trail, including superseded versions, which normal search
    excludes by default."""
    require_authorized(actor)
    return ingestion_service.get_lineage(db, lineage_id)
