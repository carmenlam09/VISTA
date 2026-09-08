"""Seeds a fixture history for standalone dev/testing. Timestamps are
relative (`days_ago`) rather than fixed dates, so archival-window tests
stay correct no matter when they're run.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.schemas.ingestion import IngestionRequest, IngestionResult
from app.schemas.record import KnowledgeRecord
from app.services.ingestion_service import IngestionService, ingestion_service

FIXTURES_PATH = Path(__file__).resolve().parent.parent.parent / "fixtures" / "sample_records.json"


def load_fixture_requests(path: str | Path | None = None) -> list[IngestionRequest]:
    data = json.loads(Path(path or FIXTURES_PATH).read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    return [
        IngestionRequest(
            entity_id=row["entity_id"],
            record_type=row["record_type"],
            timestamp=now - timedelta(days=row["days_ago"]),
            source_module=row["source_module"],
            source_reference=row["source_reference"],
            summary_text=row["summary_text"],
            tags=row.get("tags", []),
            payload=row.get("payload", {}),
        )
        for row in data
    ]


def seed_fixture_history(
    db: Session, ingestion: IngestionService | None = None, path: str | Path | None = None
) -> list[KnowledgeRecord]:
    svc = ingestion or ingestion_service
    results: list[IngestionResult] = [svc.ingest(db, request) for request in load_fixture_requests(path)]
    return [r.record for r in results]
