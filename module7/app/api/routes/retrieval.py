from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import Actor, get_current_actor, require_authorized
from app.db.session import get_db
from app.schemas.retrieval import RetrievalQuery, RetrievalResponse
from app.services.retrieval_service import retrieval_service

router = APIRouter(prefix="/api/knowledge-records", tags=["knowledge-records"])


@router.post("/search", response_model=RetrievalResponse)
def search_records(
    query: RetrievalQuery,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> RetrievalResponse:
    """Reviewer-facing search (capability 4). Historical records are
    sensitive — restricted to reviewer/admin. Results are reference context
    for the reviewer, never an automatic resolution — see the response's
    `disclaimer` field."""
    require_authorized(actor)
    return retrieval_service.search(db, query)
