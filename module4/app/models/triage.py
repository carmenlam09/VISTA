"""SQLAlchemy ORM tables, kept separate from app/schemas (the Pydantic API
contracts), matching Module 2's pattern (module2/backend/app/models/
screening.py).

Every triage run persists a fresh batch of records rather than mutating in
place — "every triage recommendation must be logged for audit purposes" is
read literally here: each generation event is itself an audit entry, not
just a cache. Previous rows for an entity are soft-archived (`is_archived`),
never deleted, on the next run, so Module 7 (or an auditor) can later see
what was recommended at any point in time. `TriageOverrideRecord` is a
separate, append-only table for reviewer overrides — including overrides of
already-archived recommendations, since a reviewer must always be able to
explain what they overrode and why.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TriageResultRecord(Base):
    __tablename__ = "triage_results"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    entity_id: Mapped[str] = mapped_column(String, index=True)
    finding_reference: Mapped[str] = mapped_column(String, index=True)
    finding_source: Mapped[str] = mapped_column(String)
    finding_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    match_quality: Mapped[dict] = mapped_column(JSON, default=dict)
    historical_outcome_signal: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence_score: Mapped[int] = mapped_column(Integer)
    disposition_recommendation: Mapped[str] = mapped_column(String, index=True)
    rationale: Mapped[str] = mapped_column(String)
    generator: Mapped[str] = mapped_column(String)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class TriageOverrideRecord(Base):
    __tablename__ = "triage_overrides"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    triage_id: Mapped[str] = mapped_column(String, index=True)
    entity_id: Mapped[str] = mapped_column(String, index=True)
    finding_reference: Mapped[str] = mapped_column(String, index=True)
    original_recommendation: Mapped[str] = mapped_column(String)
    original_confidence_score: Mapped[int] = mapped_column(Integer)
    reviewer_decision: Mapped[str] = mapped_column(String)
    reviewer_notes: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_id: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
