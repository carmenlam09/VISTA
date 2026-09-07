from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.screening import RiskCategory, SourceName


class SummaryFinding(BaseModel):
    theme: RiskCategory
    source: SourceName
    statement: str
    severity: str  # "high" | "medium" | "low" — kept as str, not enum, so the
    # LLM's output doesn't get silently dropped by strict validation.


class ScreeningSummary(BaseModel):
    entity_id: str
    narrative: str
    findings: list[SummaryFinding] = Field(default_factory=list)
    missing_or_inconclusive: list[str] = Field(default_factory=list)
    generated_at: datetime
    generator: str  # "anthropic:claude-..." or "deterministic-fallback"
