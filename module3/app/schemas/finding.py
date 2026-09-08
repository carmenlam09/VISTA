"""The AdverseMediaFinding contract — Module 3's stable output schema.

Module 4 (False Positive & True Hit Triage) is expected to consume this —
treat field names and meaning as stable once Module 4 depends on them, per
the forward-compatibility note in the spec.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.taxonomy import RiskTheme


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceHitReference(BaseModel):
    """Traceable pointer back to the exact Module 2 hit a finding came from
    — every finding must cite exactly one of these, never a blend."""

    result_id: str
    hit_id: str
    headline: str
    publication: str | None = None
    publish_date: str | None = None
    url: str | None = None
    excerpt: str


class AdverseMediaFinding(BaseModel):
    finding_id: str
    entity_id: str
    themes: list[RiskTheme]
    severity: Severity
    confidence: Confidence
    rationale: str
    matched_keywords: list[str] = Field(default_factory=list)
    source_hit: SourceHitReference
    generator: str  # "anthropic:claude-..." | "deterministic-fallback"
    created_at: datetime


class AdverseMediaScreeningResponse(BaseModel):
    entity_id: str
    findings: list[AdverseMediaFinding] = Field(default_factory=list)
    hits_considered: int
    duplicates_collapsed: int
    filtered_irrelevant: int
    suppressed_by_negation: int
