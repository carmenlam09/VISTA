"""Idempotent ingestion + versioning (capability 2). The idempotency key is
(source_module, source_reference): at most one ACTIVE row exists for a given
pair at a time.

- Resubmitting with an unchanged payload (same content_hash) is a no-op —
  the existing record is returned, nothing new is written.
- Resubmitting with a changed payload (e.g. a corrected assessment) marks
  the prior ACTIVE row SUPERSEDED (never deleted) and inserts a new ACTIVE
  row carrying the same `lineage_id`, so the full history of "this
  particular finding, over time" stays queryable as one chain.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.time import ensure_utc
from app.models.record import KnowledgeRecordORM
from app.schemas.ingestion import IngestionRequest, IngestionResult
from app.schemas.record import KnowledgeRecord, RecordStatus
from app.services.embedding import EmbeddingProvider, embedding_provider


def _compute_content_hash(source_module: str, source_reference: str, payload: dict) -> str:
    canonical = json.dumps(
        {"source_module": source_module, "source_reference": source_reference, "payload": payload},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _to_schema(orm: KnowledgeRecordORM) -> KnowledgeRecord:
    return KnowledgeRecord(
        record_id=orm.id,
        lineage_id=orm.lineage_id,
        entity_id=orm.entity_id,
        record_type=orm.record_type,
        timestamp=ensure_utc(orm.timestamp),
        source_module=orm.source_module,
        source_reference=orm.source_reference,
        status=orm.status,
        summary_text=orm.summary_text,
        tags=orm.tags,
        payload=orm.payload,
        supersedes=orm.supersedes,
        content_hash=orm.content_hash,
        created_at=ensure_utc(orm.created_at),
    )


class IngestionService:
    def __init__(self, embedder: EmbeddingProvider | None = None) -> None:
        self._embedder = embedder or embedding_provider

    def ingest(self, db: Session, request: IngestionRequest) -> IngestionResult:
        content_hash = _compute_content_hash(request.source_module, request.source_reference, request.payload)
        existing_active = self._find_active(db, request.source_module, request.source_reference)

        if existing_active is not None and existing_active.content_hash == content_hash:
            return IngestionResult(record=_to_schema(existing_active), was_duplicate=True)

        lineage_id = existing_active.lineage_id if existing_active else str(uuid.uuid4())
        superseded_id: str | None = None
        if existing_active is not None:
            existing_active.status = RecordStatus.SUPERSEDED.value
            superseded_id = existing_active.id

        embedding = self._embedder.embed(request.summary_text)
        orm = KnowledgeRecordORM(
            id=str(uuid.uuid4()),
            lineage_id=lineage_id,
            entity_id=request.entity_id,
            record_type=request.record_type.value,
            timestamp=request.timestamp,
            source_module=request.source_module,
            source_reference=request.source_reference,
            status=RecordStatus.ACTIVE.value,
            summary_text=request.summary_text,
            tags=request.tags,
            payload=request.payload,
            embedding=embedding,
            supersedes=superseded_id,
            content_hash=content_hash,
            created_at=datetime.now(timezone.utc),
        )
        db.add(orm)
        db.commit()
        db.refresh(orm)

        return IngestionResult(record=_to_schema(orm), was_duplicate=False, superseded_record_id=superseded_id)

    def get_by_id(self, db: Session, record_id: str) -> KnowledgeRecord | None:
        orm = db.query(KnowledgeRecordORM).filter(KnowledgeRecordORM.id == record_id).first()
        return _to_schema(orm) if orm else None

    def get_lineage(self, db: Session, lineage_id: str) -> list[KnowledgeRecord]:
        """Every version of the same underlying record, oldest first —
        never hidden, always retrievable for audit."""
        rows = (
            db.query(KnowledgeRecordORM)
            .filter(KnowledgeRecordORM.lineage_id == lineage_id)
            .order_by(KnowledgeRecordORM.created_at.asc())
            .all()
        )
        return [_to_schema(r) for r in rows]

    def _find_active(self, db: Session, source_module: str, source_reference: str) -> KnowledgeRecordORM | None:
        return (
            db.query(KnowledgeRecordORM)
            .filter(
                KnowledgeRecordORM.source_module == source_module,
                KnowledgeRecordORM.source_reference == source_reference,
                KnowledgeRecordORM.status == RecordStatus.ACTIVE.value,
            )
            .first()
        )


ingestion_service = IngestionService()
