"""What Module 6 reads from Modules 2-5 — its own copies of the relevant
slices of their schemas, not imports. Every downstream module in this repo
re-derives a small adapter over the modules upstream of it rather than
importing their code, since every module runs in its own venv/process.
"""

from datetime import datetime

from pydantic import BaseModel, Field

# --- Module 2 ---------------------------------------------------------


class ScreeningHitIn(BaseModel):
    hit_id: str
    title: str
    description: str
    hit_date: str | None = None
    risk_categories: list[str] = Field(default_factory=list)
    confidence: str | None = None
    raw: dict = Field(default_factory=dict)


class ScreeningResultIn(BaseModel):
    result_id: str
    entity_id: str
    source: str  # "ctos" | "netreveal" | "prior_kyv" | "adverse_news" | "public_records"
    status: str  # "ok" | "error" | "timeout"
    queried_at: datetime
    hit_count: int
    hits: list[ScreeningHitIn] = Field(default_factory=list)
    source_metadata: dict = Field(default_factory=dict)
    error_message: str | None = None


# --- Module 3 -----------------------------------------------------------


class AdverseMediaSourceHitIn(BaseModel):
    result_id: str
    hit_id: str
    headline: str
    publication: str | None = None
    publish_date: str | None = None
    url: str | None = None
    excerpt: str


class AdverseMediaFindingIn(BaseModel):
    finding_id: str
    entity_id: str
    themes: list[str] = Field(default_factory=list)
    severity: str
    confidence: str
    rationale: str
    matched_keywords: list[str] = Field(default_factory=list)
    source_hit: AdverseMediaSourceHitIn
    generator: str


# --- Module 4 -------------------------------------------------------------


class TriageFindingSummaryIn(BaseModel):
    source: str
    headline: str
    excerpt: str
    url: str | None = None
    hit_date: str | None = None
    severity: str | None = None


class TriageResultIn(BaseModel):
    triage_id: str
    entity_id: str
    finding_reference: str
    finding_source: str  # "module2" | "module3"
    finding_summary: TriageFindingSummaryIn
    match_quality: dict = Field(default_factory=dict)
    historical_outcome_signal: dict = Field(default_factory=dict)
    confidence_score: int
    disposition_recommendation: str  # "likely_false_positive" | "needs_review" | "high_priority_review"
    rationale: str
    generator: str


# --- Module 5 ---------------------------------------------------------


class EDDRecommendationIn(BaseModel):
    level: str  # "standard" | "enhanced" | "senior_escalation"
    required_steps: list[str] = Field(default_factory=list)


class MatchedRuleIn(BaseModel):
    rule_id: str
    description: str
    triggering_finding_references: list[str] = Field(default_factory=list)
    contribution: str
    rating_contribution: str  # "low" | "medium" | "high"
    edd_level: str


class RiskAssessmentDraftIn(BaseModel):
    draft_id: str
    entity_id: str
    draft_status: str  # "ai_drafted" | "reviewer_edited" | "approved"
    overall_risk_rating: str  # "low" | "medium" | "high"
    matched_rules: list[MatchedRuleIn] = Field(default_factory=list)
    materiality_justification: str
    edd_recommendation: EDDRecommendationIn
    contributing_findings: list[str] = Field(default_factory=list)
    excluded_findings: list[str] = Field(default_factory=list)
    generator: str
    created_at: datetime
