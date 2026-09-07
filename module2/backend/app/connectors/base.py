"""The ScreeningConnector interface every source integration implements.

Each real integration (CTOS, NetReveal, ...) gets exactly one implementation
of this interface. AggregationService only ever talks to this interface, so
swapping a mock for a real API client means changing one connector file and
nothing else.
"""

import hashlib
import random
from abc import ABC, abstractmethod

from app.schemas.entity import EntityProfile
from app.schemas.screening import ScreeningResult, SourceName


class ConnectorError(Exception):
    """Raised when a connector fails to produce a result for an entity."""


class ConnectorTimeoutError(ConnectorError):
    """Raised when a connector call exceeds its allotted time budget."""


def deterministic_rng(entity_id: str, source: SourceName) -> random.Random:
    """A Random seeded from (entity_id, source) so mock output is stable
    across repeated calls to the same entity/source pair, which matters for
    caching semantics and for reproducible tests."""
    seed_material = f"{entity_id}:{source.value}".encode()
    seed = int(hashlib.sha256(seed_material).hexdigest(), 16)
    return random.Random(seed)


def risk_profile(entity_id: str) -> str:
    """Stable, source-independent risk flavor for an entity: 'clean',
    'false_positive', 'moderate', or 'high_risk'. Every mock connector reads
    this so a given demo entity tells a coherent (but not identical) story
    across all five sources, the way a real vendor would."""
    seed = int(hashlib.sha256(entity_id.encode()).hexdigest(), 16)
    return ["clean", "false_positive", "moderate", "high_risk"][seed % 4]


class ScreeningConnector(ABC):
    source: SourceName

    @abstractmethod
    async def fetch(self, entity: EntityProfile) -> ScreeningResult:
        """Query this source for `entity` and return a normalized result.

        Raise ConnectorError or ConnectorTimeoutError on failure rather than
        returning a malformed result — AggregationService turns that into a
        per-source error status without failing the whole aggregation.
        """
        raise NotImplementedError
