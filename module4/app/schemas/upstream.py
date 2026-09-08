"""What Module 4 reads from Module 2 and Module 3 — its own copies of the
relevant slices of their schemas (module2/backend/app/schemas/screening.py,
module3/app/schemas/finding.py), not imports. Each downstream module in this
repo re-derives a small adapter over the modules upstream of it rather than
importing their code, since every module runs in its own venv/process.

Risk theme/category values from both upstream modules are kept as plain
strings here rather than re-declaring their enums — Module 2 uses `tax`,
Module 3 uses `tax_offence` for the same concept (see module3/README.md);
Module 4 reports whatever string it was given rather than picking a side.
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


class SourceStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"


class ScreeningHitIn(BaseModel):
    """One Module 2 ScreeningHit, source-agnostic."""

    hit_id: str
    title: str
    description: str
    hit_date: str | None = None
    risk_categories: list[str] = Field(default_factory=list)
    confidence: str | None = None
    raw: dict = Field(default_factory=dict)


class ScreeningResultIn(BaseModel):
    """One Module 2 ScreeningResult (one source, latest non-archived row)."""

    result_id: str
    entity_id: str
    source: SourceName
    status: SourceStatus
    queried_at: datetime
    hit_count: int
    hits: list[ScreeningHitIn] = Field(default_factory=list)
    source_metadata: dict = Field(default_factory=dict)
    error_message: str | None = None


class AdverseMediaSourceHitIn(BaseModel):
    result_id: str
    hit_id: str
    headline: str
    publication: str | None = None
    publish_date: str | None = None
    url: str | None = None
    excerpt: str


class AdverseMediaFindingIn(BaseModel):
    """One Module 3 AdverseMediaFinding."""

    finding_id: str
    entity_id: str
    themes: list[str] = Field(default_factory=list)
    severity: str
    confidence: str
    rationale: str
    matched_keywords: list[str] = Field(default_factory=list)
    source_hit: AdverseMediaSourceHitIn
    generator: str
