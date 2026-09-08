"""Audit logging (NEW — Module 1 had none before this refactor). Matches
Module 2's audit_service.py pattern: every extraction run and every save is
logged permanently; nothing is ever deleted."""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLogRecord(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    actor_id: Mapped[str] = mapped_column(String, index=True)
    actor_role: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String, index=True)  # "extraction" | "save" | "view"
    vendor_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
