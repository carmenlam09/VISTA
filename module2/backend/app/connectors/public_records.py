import asyncio
import uuid
from datetime import datetime, timezone

from app.connectors.base import ConnectorTimeoutError, ScreeningConnector, deterministic_rng, risk_profile
from app.schemas.entity import EntityProfile
from app.schemas.screening import (
    MatchConfidence,
    RiskCategory,
    ScreeningHit,
    ScreeningResult,
    SourceName,
    SourceStatus,
)

REGISTRIES = ["Companies Registry", "Court Records", "Tax Authority Registry", "Land Registry"]


class PublicRecordsConnector(ScreeningConnector):
    """Mock connector over public registries, litigation, and sanctions lists."""

    source = SourceName.PUBLIC_RECORDS

    async def fetch(self, entity: EntityProfile) -> ScreeningResult:
        rng = deterministic_rng(entity.entity_id, self.source)
        await asyncio.sleep(rng.uniform(0.05, 0.2))

        if rng.random() < 0.06:
            raise ConnectorTimeoutError(f"Public records lookup timed out for {entity.entity_id}")

        profile = risk_profile(entity.entity_id)
        hits: list[ScreeningHit] = []

        if profile == "moderate":
            hits.append(
                ScreeningHit(
                    hit_id=str(uuid.uuid4()),
                    title="Civil litigation on record",
                    description=f"Court registry shows an active civil suit naming {entity.legal_name} as a party.",
                    hit_date="2024-07-19",
                    risk_categories=[RiskCategory.OPERATIONAL],
                    confidence=MatchConfidence.MEDIUM,
                    raw={"registry": "Court Records", "case_status": "active"},
                )
            )
        elif profile == "high_risk":
            hits.append(
                ScreeningHit(
                    hit_id=str(uuid.uuid4()),
                    title="Outstanding tax arrears",
                    description=f"Public tax registry lists outstanding arrears for {entity.legal_name}.",
                    hit_date="2025-01-08",
                    risk_categories=[RiskCategory.TAX],
                    confidence=MatchConfidence.HIGH,
                    raw={"registry": "Tax Authority Registry", "arrears_status": "outstanding"},
                )
            )

        return ScreeningResult(
            result_id=str(uuid.uuid4()),
            entity_id=entity.entity_id,
            source=self.source,
            status=SourceStatus.OK,
            queried_at=datetime.now(timezone.utc),
            hit_count=len(hits),
            risk_categories=sorted({c for h in hits for c in h.risk_categories}, key=lambda c: c.value),
            match_confidence=hits[0].confidence if hits else None,
            hits=hits,
            source_metadata={"registries_checked": REGISTRIES},
        )
