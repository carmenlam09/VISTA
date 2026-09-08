"""SQLAlchemy ORM table for the knowledge repository. There is deliberately
no delete path anywhere in this module — `ingestion_service.py` and
`retrieval_service.py` only ever INSERT and UPDATE `status`/`supersedes` on
existing rows, never DELETE. Every row, once written, exists forever; this
is a regulated bank's audit trail.

`embedding` stores the local hashed-TF vector (see app/services/embedding.py)
as a JSON list of floats — a plain column in the same SQLite database, not a
separate vector store, since query-time cosine similarity over this table's
realistic size is more than fast enough and this avoids a second piece of
infrastructure (see README "Storage & retrieval approach").
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeRecordORM(Base):
    __tablename__ = "knowledge_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    lineage_id: Mapped[str] = mapped_column(String, index=True)
    entity_id: Mapped[str] = mapped_column(String, index=True)
    record_type: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_module: Mapped[str] = mapped_column(String, index=True)
    source_reference: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, index=True)
    summary_text: Mapped[str] = mapped_column(String)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    embedding: Mapped[list] = mapped_column(JSON, default=list)
    supersedes: Mapped[str | None] = mapped_column(String, nullable=True)
    content_hash: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
