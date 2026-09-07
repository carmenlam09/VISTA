"""The ScreeningResult contract.

This is the schema Module 3 (Adverse Media Screening Engine) and Module 4
(False Positive & True Hit Triage) are expected to consume, per the forward
compatibility notes in the spec — treat field names and meaning as stable
once other modules depend on them.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SourceName(str, Enum):
    CTOS = "ctos"
    NETREVEAL = "netreveal"
    PRIOR_KYV = "prior_kyv"
    ADVERSE_NEWS = "adverse_news"
    PUBLIC_RECORDS = "public_records"


class RiskCategory(str, Enum):
    FINANCIAL_CRIME = "financial_crime"
    SANCTIONS = "sanctions"
    FRAUD = "fraud"
    REGULATORY_BREACH = "regulatory_breach"
    TAX = "tax"
    ESG = "esg"
    OPERATIONAL = "operational"


class SourceStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"


class MatchConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ScreeningHit(BaseModel):
    hit_id: str
    title: str
    description: str
    hit_date: str | None = None
    risk_categories: list[RiskCategory] = Field(default_factory=list)
    confidence: MatchConfidence
    raw: dict = Field(default_factory=dict)


class ScreeningResult(BaseModel):
    """Normalized output of one connector for one entity, one point in time."""

    result_id: str
    entity_id: str
    source: SourceName
    status: SourceStatus
    queried_at: datetime
    hit_count: int
    risk_categories: list[RiskCategory] = Field(default_factory=list)
    match_confidence: MatchConfidence | None = None
    hits: list[ScreeningHit] = Field(default_factory=list)
    source_metadata: dict = Field(default_factory=dict)
    error_message: str | None = None
    is_archived: bool = False


class SourceStatusBadge(str, Enum):
    """Summarized status for the entity list view."""

    CLEAR = "clear"
    HITS_FOUND = "hits_found"
    NEEDS_REFRESH = "needs_refresh"
    SOURCE_UNAVAILABLE = "source_unavailable"


class EntityScreeningStatus(BaseModel):
    entity_id: str
    legal_name: str
    entity_type: str
    badge: SourceStatusBadge
    total_hits: int
    sources_queried: int
    sources_unavailable: int
    last_queried_at: datetime | None = None


class AggregationResponse(BaseModel):
    entity_id: str
    results: list[ScreeningResult]
    requested_sources: list[SourceName]
    succeeded_sources: list[SourceName]
    failed_sources: list[SourceName]
