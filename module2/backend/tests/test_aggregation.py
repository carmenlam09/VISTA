from app.schemas.screening import SourceName, SourceStatus
from app.services.aggregation_service import aggregation_service
from app.services.entity_service import entity_service


async def test_aggregate_survives_partial_source_failure(db_session):
    entity = entity_service.get_entity("vendor:1")
    response = await aggregation_service.aggregate(db_session, entity, force_refresh=True)

    assert len(response.results) == 5
    assert SourceName.NETREVEAL in response.failed_sources

    netreveal_result = next(r for r in response.results if r.source == SourceName.NETREVEAL)
    assert netreveal_result.status == SourceStatus.TIMEOUT
    assert netreveal_result.error_message

    other_results = [r for r in response.results if r.source != SourceName.NETREVEAL]
    assert all(r.status == SourceStatus.OK for r in other_results)


async def test_aggregate_reuses_fresh_cache_without_requerying(db_session):
    entity = entity_service.get_entity("vendor:4")
    first = await aggregation_service.aggregate(db_session, entity, force_refresh=True)
    second = await aggregation_service.aggregate(db_session, entity, force_refresh=False)

    first_ids = {r.source: r.result_id for r in first.results}
    second_ids = {r.source: r.result_id for r in second.results}
    assert first_ids == second_ids


async def test_force_refresh_bypasses_cache(db_session):
    entity = entity_service.get_entity("vendor:4")
    first = await aggregation_service.aggregate(db_session, entity, force_refresh=True)
    second = await aggregation_service.aggregate(db_session, entity, force_refresh=True)

    first_ids = {r.source: r.result_id for r in first.results}
    second_ids = {r.source: r.result_id for r in second.results}
    assert first_ids != second_ids


async def test_get_cached_returns_latest_non_archived_rows(db_session):
    entity = entity_service.get_entity("vendor:9")
    await aggregation_service.aggregate(db_session, entity, force_refresh=True)

    cached = aggregation_service.get_cached(db_session, entity.entity_id)
    assert len(cached) == 5
    assert all(not r.is_archived for r in cached)


async def test_refresh_archives_previous_row_instead_of_deleting(db_session):
    from app.models.screening import ScreeningResultRecord

    entity = entity_service.get_entity("vendor:9")
    await aggregation_service.aggregate(db_session, entity, force_refresh=True)
    await aggregation_service.aggregate(db_session, entity, force_refresh=True)

    all_rows = (
        db_session.query(ScreeningResultRecord).filter(ScreeningResultRecord.entity_id == entity.entity_id).all()
    )
    assert len(all_rows) == 10  # 5 sources x 2 runs, old rows archived not deleted
    assert sum(1 for r in all_rows if r.is_archived) == 5
