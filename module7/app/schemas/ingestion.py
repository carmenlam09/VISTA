"""The ingestion API contract (capability 2). Any of Modules 1-6 (or a
future integration pass) submits an `IngestionRequest`; the server computes
`record_id`, `lineage_id` (new on first submission, carried forward on a
superseding resubmission), `content_hash`, `status`, and `created_at` —
callers never set those themselves, since idempotency depends on the server
being the one source of truth for what counts as "the same" record.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.record import KnowledgeRecord, RecordType


class IngestionRequest(BaseModel):
    entity_id: str
    record_type: RecordType
    timestamp: datetime
    source_module: str
    source_reference: str
    summary_text: str
    tags: list[str] = Field(default_factory=list)
    payload: dict = Field(default_factory=dict)


class IngestionResult(BaseModel):
    record: KnowledgeRecord
    was_duplicate: bool  # True if this exact content had already been ingested (no-op, existing record returned)
    superseded_record_id: str | None = None  # set if this ingestion superseded a prior version
