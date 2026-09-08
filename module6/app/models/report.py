"""SQLAlchemy ORM tables, kept separate from app/schemas, matching Modules
2/4/5's pattern.

Unlike Module 4/5's single-active-row-plus-soft-archive pattern, every
report generation is its own permanent row keyed by (entity_id, version) —
"regenerating a report... should produce a new version, not silently
overwrite history" is the whole point here, so there is no is_archived flag:
every version stays first-class and queryable, and "latest" is simply the
highest version number for that entity. `ReportHistoryRecord` is a separate,
append-only table logging both generation events and status transitions.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GeneratedReportRecord(Base):
    __tablename__ = "generated_reports"
    __table_args__ = (UniqueConstraint("entity_id", "version", name="uq_report_entity_version"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    entity_id: Mapped[str] = mapped_column(String, index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, index=True)
    file_path: Mapped[str] = mapped_column(String)
    narrative: Mapped[dict] = mapped_column(JSON, default=dict)
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)
    missing_sections: Mapped[list] = mapped_column(JSON, default=list)
    generator: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ReportHistoryRecord(Base):
    __tablename__ = "report_history"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    report_id: Mapped[str] = mapped_column(String, index=True)
    entity_id: Mapped[str] = mapped_column(String, index=True)
    version: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String, index=True)  # "generated" | "status_changed"
    actor_id: Mapped[str] = mapped_column(String, index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
