"""SQLAlchemy ORM tables. Kept separate from app/schemas (the Pydantic API
contracts) so the storage shape can evolve independently of the API shape.

Old rows are never hard-deleted (`is_archived` marks superseded rows instead)
so Module 7 (Vendor Risk Knowledge Repository) can later read historical
aggregation runs.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScreeningResultRecord(Base):
    __tablename__ = "screening_results"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    entity_id: Mapped[str] = mapped_column(String, index=True)
    source: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String)
    queried_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    risk_categories: Mapped[list] = mapped_column(JSON, default=list)
    match_confidence: Mapped[str | None] = mapped_column(String, nullable=True)
    hits: Mapped[list] = mapped_column(JSON, default=list)
    source_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AuditLogRecord(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    actor_id: Mapped[str] = mapped_column(String, index=True)
    actor_role: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String, index=True)  # "query" | "view" | "refresh"
    entity_id: Mapped[str] = mapped_column(String, index=True)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
