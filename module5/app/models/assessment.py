"""SQLAlchemy ORM tables, kept separate from app/schemas, matching Module 2
and Module 4's pattern.

Every `run_assessment` call persists a fresh draft, soft-archiving the
entity's previous one rather than overwriting it — "every draft, and every
subsequent reviewer edit or override of it, must be logged" is read
literally, mirroring Module 4's audit_service.py. `DraftHistoryRecord` is a
separate, append-only table covering the full lifecycle: the initial
AI draft, every reviewer edit, and the final approval.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RiskAssessmentDraftRecord(Base):
    __tablename__ = "risk_assessment_drafts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    entity_id: Mapped[str] = mapped_column(String, index=True)
    draft_status: Mapped[str] = mapped_column(String, index=True)
    overall_risk_rating: Mapped[str] = mapped_column(String)
    matched_rules: Mapped[list] = mapped_column(JSON, default=list)
    materiality_justification: Mapped[str] = mapped_column(String)
    edd_level: Mapped[str] = mapped_column(String)
    edd_required_steps: Mapped[list] = mapped_column(JSON, default=list)
    contributing_findings: Mapped[list] = mapped_column(JSON, default=list)
    excluded_findings: Mapped[list] = mapped_column(JSON, default=list)
    generator: Mapped[str] = mapped_column(String)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class DraftHistoryRecord(Base):
    __tablename__ = "draft_history"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    draft_id: Mapped[str] = mapped_column(String, index=True)
    entity_id: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String, index=True)  # "drafted" | "edited" | "approved"
    actor_id: Mapped[str] = mapped_column(String, index=True)
    changes: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
