from fastapi import APIRouter

from app.schemas.finding import AdverseMediaScreeningResponse
from app.services.screening_engine import screening_engine

router = APIRouter(prefix="/api/entities/{entity_id}/adverse-media-findings", tags=["adverse-media"])


@router.get("", response_model=AdverseMediaScreeningResponse)
async def get_adverse_media_findings(entity_id: str) -> AdverseMediaScreeningResponse:
    """Runs the full pipeline (fetch -> dedup -> filter -> categorize) fresh
    on every call — Module 3 does not cache; Module 2 already owns caching
    for the underlying adverse-news hits this reads."""
    return await screening_engine.screen_entity(entity_id)
