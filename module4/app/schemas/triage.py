"""The TriageResult contract — Module 4's stable output schema.

Module 5 (Risk Assessment & EDD Recommendation) is expected to consume this
— treat field names and meaning as stable once Module 5 depends on them, per
the forward-compatibility note in the spec.

Every TriageResult carries `label`, a constant string, specifically so no
caller can present this as a resolved status by accident — every consumer
of this schema sees, in the data itself, that this is a pending
recommendation. See the "Hard Requirement" section of the Module 4 prompt.
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class FindingSource(str, Enum):
    MODULE2 = "module2"
    MODULE3 = "module3"


class Disposition(str, Enum):
    LIKELY_FALSE_POSITIVE = "likely_false_positive"
    NEEDS_REVIEW = "needs_review"
    HIGH_PRIORITY_REVIEW = "high_priority_review"


class HistoricalPriorOutcome(str, Enum):
    FALSE_POSITIVE = "false_positive"
    TRUE_HIT = "true_hit"
    UNKNOWN = "unknown"


class FindingSummary(BaseModel):
    """Enough of the underlying Module 2 hit / Module 3 finding to display
    without a second lookup — headline/excerpt plus where it came from."""

    source: str  # e.g. "ctos", "adverse_news"
    headline: str
    excerpt: str
    url: str | None = None
    hit_date: str | None = None
    severity: str | None = None  # Module 3's severity for adverse-media findings, or Module 2's
    # hit-level match_confidence for the other four sources — both are high/medium/low signal-
    # strength indicators from upstream, used as a scoring input, not restated as a new concept.


class MatchQuality(BaseModel):
    name_similarity_score: float = Field(ge=0.0, le=1.0)
    matched_name: str | None = None  # the name string the finding text was compared against, for transparency
    nationality_match: bool
    id_match: bool
    ownership_overlap_score: float = Field(ge=0.0, le=1.0)
    matched_related_entities: list[str] = Field(default_factory=list)


class HistoricalOutcomeSignal(BaseModel):
    prior_review_found: bool
    prior_outcome: HistoricalPriorOutcome
    prior_review_date: date | None = None
    prior_review_note: str | None = None


class TriageResult(BaseModel):
    triage_id: str
    entity_id: str
    finding_reference: str
    finding_source: FindingSource
    finding_summary: FindingSummary
    match_quality: MatchQuality
    historical_outcome_signal: HistoricalOutcomeSignal
    confidence_score: int = Field(ge=0, le=100)
    disposition_recommendation: Disposition
    rationale: str
    generator: str  # "anthropic:claude-..." | "deterministic-fallback"
    created_at: datetime
    label: str = "AI-suggested — pending human confirmation, not a resolved status"


class TriageRunResponse(BaseModel):
    entity_id: str
    results: list[TriageResult] = Field(default_factory=list)
    generated_at: datetime


class ReviewerDecision(str, Enum):
    CONFIRMED_TRUE_HIT = "confirmed_true_hit"
    CONFIRMED_FALSE_POSITIVE = "confirmed_false_positive"
    ESCALATED = "escalated"
    OTHER = "other"


class OverrideRequest(BaseModel):
    reviewer_decision: ReviewerDecision
    reviewer_notes: str | None = None


class OverrideRecord(BaseModel):
    override_id: str
    triage_id: str
    entity_id: str
    finding_reference: str
    original_recommendation: Disposition
    original_confidence_score: int
    reviewer_decision: ReviewerDecision
    reviewer_notes: str | None = None
    actor_id: str
    created_at: datetime
