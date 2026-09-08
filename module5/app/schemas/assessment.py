"""The RiskAssessmentDraft contract — Module 5's stable output schema.

Module 6 (Smart KYV Report Generation) is expected to consume this — treat
field names and meaning as stable once Module 6 depends on them.

Every draft carries `label`, a constant string, for the same reason Module
4's TriageResult does: no caller can present this as a final, approved
assessment by accident. `draft_status` additionally tracks the Maker-Checker
lifecycle explicitly (ai_drafted -> reviewer_edited -> approved).
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.policy import EDDLevel, RiskRating


class DraftStatus(str, Enum):
    AI_DRAFTED = "ai_drafted"
    REVIEWER_EDITED = "reviewer_edited"
    APPROVED = "approved"


class EDDRecommendation(BaseModel):
    level: EDDLevel
    required_steps: list[str] = Field(default_factory=list)


class MatchedRule(BaseModel):
    rule_id: str
    description: str
    triggering_finding_references: list[str]
    contribution: str  # human-readable, e.g. "raises rating to medium due to an unresolved sanctions-theme hit"
    rating_contribution: RiskRating
    edd_level: EDDLevel


class RiskAssessmentDraft(BaseModel):
    draft_id: str
    entity_id: str
    draft_status: DraftStatus
    overall_risk_rating: RiskRating
    matched_rules: list[MatchedRule] = Field(default_factory=list)
    materiality_justification: str
    edd_recommendation: EDDRecommendation
    contributing_findings: list[str] = Field(default_factory=list)
    excluded_findings: list[str] = Field(default_factory=list)
    generator: str  # "anthropic:claude-..." | "deterministic-fallback"
    created_at: datetime
    label: str = "AI-drafted — pending reviewer review and approval, not a final assessment"


class DraftEditRequest(BaseModel):
    """A reviewer's edit to a draft's conclusions. Every field is optional —
    a reviewer edits only what they disagree with; unset fields keep the
    AI-drafted value."""

    overall_risk_rating: RiskRating | None = None
    edd_level: EDDLevel | None = None
    edd_required_steps: list[str] | None = None
    materiality_justification: str | None = None
    edit_notes: str | None = None


class DraftApprovalRequest(BaseModel):
    approval_notes: str | None = None


class DraftHistoryEntry(BaseModel):
    history_id: str
    draft_id: str
    entity_id: str
    action: str  # "drafted" | "edited" | "approved"
    actor_id: str
    changes: dict = Field(default_factory=dict)
    notes: str | None = None
    created_at: datetime
