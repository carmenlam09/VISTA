"""Concurrent multi-source aggregation with caching and partial-failure
handling. This is Module 4's expected entry point into the full aggregated
result set — keep `aggregate` and `get_cached` as clean, UI-independent
functions."""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.connectors.base import ConnectorError
from app.connectors.registry import CONNECTOR_REGISTRY
from app.core.config import settings
from app.core.time import ensure_utc
from app.models.screening import ScreeningResultRecord
from app.schemas.entity import EntityProfile
from app.schemas.screening import AggregationResponse, ScreeningResult, SourceName, SourceStatus
from app.services.cache_service import cache_service


def _record_to_schema(record: ScreeningResultRecord) -> ScreeningResult:
    return ScreeningResult(
        result_id=record.id,
        entity_id=record.entity_id,
        source=record.source,
        status=record.status,
        queried_at=ensure_utc(record.queried_at),
        hit_count=record.hit_count,
        risk_categories=record.risk_categories,
        match_confidence=record.match_confidence,
        hits=record.hits,
        source_metadata=record.source_metadata,
        error_message=record.error_message,
        is_archived=record.is_archived,
    )


def _result_to_record(result: ScreeningResult) -> ScreeningResultRecord:
    return ScreeningResultRecord(
        id=result.result_id,
        entity_id=result.entity_id,
        source=result.source.value,
        status=result.status.value,
        queried_at=result.queried_at,
        hit_count=result.hit_count,
        risk_categories=[c.value for c in result.risk_categories],
        match_confidence=result.match_confidence.value if result.match_confidence else None,
        hits=[h.model_dump(mode="json") for h in result.hits],
        source_metadata=result.source_metadata,
        error_message=result.error_message,
        is_archived=False,
    )


def _error_result(source: SourceName, entity_id: str, status: SourceStatus, message: str) -> ScreeningResult:
    return ScreeningResult(
        result_id=str(uuid.uuid4()),
        entity_id=entity_id,
        source=source,
        status=status,
        queried_at=datetime.now(timezone.utc),
        hit_count=0,
        error_message=message,
    )


async def _query_one(source: SourceName, entity: EntityProfile) -> ScreeningResult:
    connector = CONNECTOR_REGISTRY[source]
    try:
        return await asyncio.wait_for(connector.fetch(entity), timeout=settings.connector_timeout_seconds)
    except asyncio.TimeoutError:
        return _error_result(
            source,
            entity.entity_id,
            SourceStatus.TIMEOUT,
            f"{source.value} did not respond within {settings.connector_timeout_seconds}s",
        )
    except ConnectorError as exc:
        status = SourceStatus.TIMEOUT if "timed out" in str(exc).lower() else SourceStatus.ERROR
        return _error_result(source, entity.entity_id, status, str(exc))
    except Exception as exc:  # noqa: BLE001 — one bad connector must never take the whole aggregation down
        return _error_result(source, entity.entity_id, SourceStatus.ERROR, f"Unexpected connector failure: {exc}")


class AggregationService:
    async def aggregate(
        self,
        db: Session,
        entity: EntityProfile,
        sources: list[SourceName] | None = None,
        force_refresh: bool = False,
    ) -> AggregationResponse:
        requested = sources or list(CONNECTOR_REGISTRY.keys())
        to_query: list[SourceName] = []
        results: list[ScreeningResult] = []

        for source in requested:
            cached = None if force_refresh else cache_service.get_fresh(db, entity.entity_id, source)
            if cached is not None:
                results.append(_record_to_schema(cached))
            else:
                to_query.append(source)

        if to_query:
            fetched = await asyncio.gather(*(_query_one(source, entity) for source in to_query))
            for result in fetched:
                cache_service.store(db, _result_to_record(result))
                results.append(result)

        succeeded = [r.source for r in results if r.status == SourceStatus.OK]
        failed = [r.source for r in results if r.status != SourceStatus.OK]

        return AggregationResponse(
            entity_id=entity.entity_id,
            results=results,
            requested_sources=requested,
            succeeded_sources=succeeded,
            failed_sources=failed,
        )

    def get_cached(self, db: Session, entity_id: str) -> list[ScreeningResult]:
        return [_record_to_schema(r) for r in cache_service.get_latest(db, entity_id)]


aggregation_service = AggregationService()
