"""Per-source, per-entity TTL cache backed by the screening_results table."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import ensure_utc
from app.models.screening import ScreeningResultRecord
from app.schemas.screening import SourceName


class CacheService:
    def __init__(self, ttl_seconds: int | None = None) -> None:
        self.ttl_seconds = ttl_seconds if ttl_seconds is not None else settings.screening_cache_ttl_seconds

    def get_fresh(self, db: Session, entity_id: str, source: SourceName) -> ScreeningResultRecord | None:
        record = self._latest(db, entity_id, source)
        if record is None or self._is_stale(record.queried_at):
            return None
        return record

    def get_latest(self, db: Session, entity_id: str) -> list[ScreeningResultRecord]:
        return (
            db.query(ScreeningResultRecord)
            .filter(
                ScreeningResultRecord.entity_id == entity_id,
                ScreeningResultRecord.is_archived.is_(False),
            )
            .order_by(ScreeningResultRecord.source)
            .all()
        )

    def store(self, db: Session, record: ScreeningResultRecord) -> None:
        """Soft-archives the current row for this entity/source (never
        deletes it — Module 7 will eventually read archived runs) and
        inserts the new one."""
        db.query(ScreeningResultRecord).filter(
            ScreeningResultRecord.entity_id == record.entity_id,
            ScreeningResultRecord.source == record.source,
            ScreeningResultRecord.is_archived.is_(False),
        ).update({"is_archived": True})
        db.add(record)
        db.commit()

    def _latest(self, db: Session, entity_id: str, source: SourceName) -> ScreeningResultRecord | None:
        return (
            db.query(ScreeningResultRecord)
            .filter(
                ScreeningResultRecord.entity_id == entity_id,
                ScreeningResultRecord.source == source.value,
                ScreeningResultRecord.is_archived.is_(False),
            )
            .order_by(ScreeningResultRecord.queried_at.desc())
            .first()
        )

    def _is_stale(self, queried_at: datetime) -> bool:
        return datetime.now(timezone.utc) - ensure_utc(queried_at) > timedelta(seconds=self.ttl_seconds)


cache_service = CacheService()
