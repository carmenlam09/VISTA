import pytest

from app.connectors.base import ConnectorTimeoutError
from app.connectors.registry import CONNECTOR_REGISTRY
from app.schemas.screening import SourceName, SourceStatus
from app.services.entity_service import entity_service


def _entity(entity_id: str):
    entity = entity_service.get_entity(entity_id)
    assert entity is not None, f"fixture entity {entity_id} missing"
    return entity


async def test_high_risk_entity_has_hits_across_all_sources():
    """vendor:4 is the bundled 'genuinely risky' fixture entity."""
    entity = _entity("vendor:4")
    for source, connector in CONNECTOR_REGISTRY.items():
        result = await connector.fetch(entity)
        assert result.source == source
        assert result.entity_id == entity.entity_id
        assert result.status == SourceStatus.OK
        assert result.hit_count >= 1
        assert result.match_confidence is not None


async def test_clean_entity_has_no_hits():
    """vendor:9 is the bundled 'clean' fixture entity."""
    entity = _entity("vendor:9")
    for connector in CONNECTOR_REGISTRY.values():
        result = await connector.fetch(entity)
        assert result.status == SourceStatus.OK
        assert result.hit_count == 0
        assert result.hits == []


async def test_connector_raises_on_simulated_source_failure():
    """vendor:1 is the bundled fixture whose NetReveal call deterministically
    fails — this is what AggregationService's partial-failure handling is
    tested against."""
    entity = _entity("vendor:1")
    with pytest.raises(ConnectorTimeoutError):
        await CONNECTOR_REGISTRY[SourceName.NETREVEAL].fetch(entity)


async def test_hit_shape_is_normalized():
    entity = _entity("vendor:4")
    result = await CONNECTOR_REGISTRY[SourceName.CTOS].fetch(entity)
    hit = result.hits[0]
    assert hit.hit_id
    assert hit.title
    assert hit.confidence is not None
    assert isinstance(hit.risk_categories, list)
