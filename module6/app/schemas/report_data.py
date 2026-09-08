"""ReportData — the unified aggregation of an entity's data across Modules
1-5 (capability 1). Every section carries an explicit `status` so missing
upstream data is flagged in the report, never silently omitted or left
blank without explanation — per the spec's hard requirement.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.entity import EntityProfile
from app.schemas.upstream import AdverseMediaFindingIn, RiskAssessmentDraftIn, ScreeningResultIn, TriageResultIn


class SectionStatus(str, Enum):
    OK = "ok"
    MISSING = "missing"  # upstream module has no data for this entity yet
    ERROR = "error"  # upstream read failed (DB unavailable, live call failed, etc.)


class EntityProfileSection(BaseModel):
    status: SectionStatus
    note: str | None = None
    profile: EntityProfile | None = None


class ScreeningEvidenceSection(BaseModel):
    status: SectionStatus
    note: str | None = None
    results: list[ScreeningResultIn] = Field(default_factory=list)


class AdverseMediaSection(BaseModel):
    status: SectionStatus
    note: str | None = None
    findings: list[AdverseMediaFindingIn] = Field(default_factory=list)


class TriageSection(BaseModel):
    status: SectionStatus
    note: str | None = None
    results: list[TriageResultIn] = Field(default_factory=list)


class RiskAssessmentSection(BaseModel):
    status: SectionStatus
    note: str | None = None
    assessment: RiskAssessmentDraftIn | None = None


class ReportData(BaseModel):
    entity_id: str
    entity: EntityProfileSection
    screening_evidence: ScreeningEvidenceSection
    adverse_media: AdverseMediaSection
    triage: TriageSection
    risk_assessment: RiskAssessmentSection
    aggregated_at: datetime
