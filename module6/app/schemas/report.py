"""The GeneratedReport contract — Module 6's stable output schema.

Every report carries a constant `label` (matching the pattern established by
Module 4's TriageResult and Module 5's RiskAssessmentDraft) so no caller can
present a generated report as final by accident. `status` tracks the
draft -> under_review -> approved lifecycle explicitly.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ReportStatus(str, Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"


class NarrativeSection(BaseModel):
    section_id: str
    title: str
    text: str
    generator: str  # "anthropic:claude-..." | "deterministic-fallback"


class ReportNarrative(BaseModel):
    executive_summary: NarrativeSection
    screening_findings_summary: NarrativeSection
    adverse_media_narrative: NarrativeSection
    risk_assessment_narrative: NarrativeSection
    edd_recommendation_writeup: NarrativeSection

    def sections(self) -> list[NarrativeSection]:
        return [
            self.executive_summary,
            self.screening_findings_summary,
            self.adverse_media_narrative,
            self.risk_assessment_narrative,
            self.edd_recommendation_writeup,
        ]


class TraceabilityEntry(BaseModel):
    section_id: str
    claim: str  # short description of what's being cited, e.g. "3 high-priority findings referenced"
    source_module: str  # "module1" | "module2" | "module3" | "module4" | "module5"
    source_references: list[str] = Field(default_factory=list)  # finding_references, rule_ids, entity_id, etc.


class TraceabilityManifest(BaseModel):
    entity_id: str
    report_id: str
    version: int
    entries: list[TraceabilityEntry] = Field(default_factory=list)
    generated_at: datetime


class GeneratedReport(BaseModel):
    report_id: str
    entity_id: str
    version: int
    status: ReportStatus
    file_path: str  # path to the generated .docx, relative to generated_reports_dir
    narrative: ReportNarrative
    manifest: TraceabilityManifest
    missing_sections: list[str] = Field(default_factory=list)  # section_ids flagged incomplete
    generator: str
    created_at: datetime
    label: str = "AI-drafted KYV report — pending reviewer sign-off, not final or approved"


class ReportStatusChangeRequest(BaseModel):
    status: ReportStatus
    notes: str | None = None


class ReportHistoryEntry(BaseModel):
    history_id: str
    report_id: str
    entity_id: str
    version: int
    action: str  # "generated" | "status_changed"
    actor_id: str
    details: dict = Field(default_factory=dict)
    notes: str | None = None
    created_at: datetime
