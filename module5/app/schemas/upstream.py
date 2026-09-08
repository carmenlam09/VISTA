"""What Module 5 reads from Module 4 — its own copy of the relevant slice of
Module 4's schema (module4/app/schemas/triage.py), not an import.

`match_quality` and `historical_outcome_signal` are kept as loose dicts
rather than fully re-modeled: Module 5's rule engine matches on theme,
severity, confidence, disposition, and entity attributes, not on the
entity-resolution sub-scores themselves, so there's no need to duplicate
that whole schema here — the data still round-trips into the draft response
for display.

`EnrichedFinding` is Module 5's own addition, not part of Module 4's output:
Module 4's FindingSummary doesn't carry the risk theme through from either
Module 2's `risk_categories` or Module 3's `themes` (a real gap discovered
building Module 5 — see module5/README.md). `theme_enrichment.py` recovers
it by parsing `finding_reference` and reading the original Module 2 hit /
Module 3 finding directly.
"""

from pydantic import BaseModel, Field


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


class EnrichedFinding(BaseModel):
    triage: TriageResultIn
    themes: list[str] = Field(default_factory=list)
