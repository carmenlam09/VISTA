"""The retrieval query interface (capability 3/4). Combines structured
filtering (entity, record type, tags, date range) with an optional freeform
`query_text` ranked by semantic similarity — a reviewer can supply either or
both. Results are reference context, never a decision: every
`RetrievalResult` is framed as something for a human to judge, which is why
`match_reason` exists — a reviewer should see *why* something surfaced, not
just a bare score.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.record import KnowledgeRecord, RecordType


class RetrievalQuery(BaseModel):
    query_text: str | None = None
    entity_id: str | None = None
    record_type: RecordType | None = None
    tags: list[str] = Field(default_factory=list)  # a record matches if it has ANY of these tags
    date_from: date | None = None
    date_to: date | None = None
    include_archived: bool = False  # retention-policy-aged-out records excluded from default results
    include_superseded: bool = False  # superseded versions excluded from default results
    limit: int = Field(default=10, ge=1, le=100)


class RetrievalResult(BaseModel):
    record: KnowledgeRecord
    relevance_score: float = Field(ge=0.0, le=1.0)
    match_reason: str  # e.g. "semantic similarity 0.82; entity match; tag 'false_positive'"
    is_archived: bool  # per current retention policy, computed at query time


class RetrievalResponse(BaseModel):
    results: list[RetrievalResult]
    query_echo: RetrievalQuery
    generated_at: datetime
    disclaimer: str = (
        "These are historical reference records for reviewer context. They are not a "
        "recommendation and must not be treated as an automatic resolution of a new finding."
    )
