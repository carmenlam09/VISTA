"""The KnowledgeRecord contract — Module 7's unified schema for everything
it captures (capability 1). Every record type from every source module maps
onto this one shape; `payload` carries the type-specific detail as an opaque
dict, `summary_text` carries the narrative/rationale text used for semantic
retrieval, and `tags` carries structured, filterable labels (risk themes,
dispositions, outcomes) — populated by whatever calls the ingestion API,
since only that caller knows how to derive them from its own record shape.

`lineage_id` and `content_hash` exist purely to make ingestion idempotent
and versioned (capability 2) — see ingestion_service.py. Nothing is ever
hard-deleted: a corrected record supersedes the prior version, which stays
in the table with `status=superseded`, forever retrievable.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RecordType(str, Enum):
    KYV_REVIEW = "kyv_review"
    ADVERSE_NEWS_ASSESSMENT = "adverse_news_assessment"
    FALSE_POSITIVE_DECISION = "false_positive_decision"
    EDD_OUTCOME = "edd_outcome"
    APPROVAL_RECORD = "approval_record"


class RecordStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class KnowledgeRecord(BaseModel):
    record_id: str
    lineage_id: str  # groups every version of "the same" underlying record across supersessions
    entity_id: str
    record_type: RecordType
    timestamp: datetime  # when the underlying event/decision happened, per the source module
    source_module: str  # "module3" | "module4" | "module5" | "module6" | ...
    source_reference: str  # stable id from the source module (finding_id/draft_id/report_id/...)
    status: RecordStatus
    summary_text: str  # narrative/rationale text — embedded for semantic retrieval, shown to reviewers
    tags: list[str] = Field(default_factory=list)  # e.g. risk themes, "false_positive", "senior_escalation"
    payload: dict = Field(default_factory=dict)  # the actual assessment/finding data, source-module-shaped
    supersedes: str | None = None  # record_id of the version this replaces, if any
    content_hash: str  # hash of (source_module, source_reference, payload) — idempotency key
    created_at: datetime  # when Module 7 ingested this version
