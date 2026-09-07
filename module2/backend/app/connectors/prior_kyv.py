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


class PriorKYVConnector(ScreeningConnector):
    """Mock connector over internal historical KYV review outcomes."""

    source = SourceName.PRIOR_KYV

    async def fetch(self, entity: EntityProfile) -> ScreeningResult:
        rng = deterministic_rng(entity.entity_id, self.source)
        await asyncio.sleep(rng.uniform(0.02, 0.1))

        if rng.random() < 0.03:
            raise ConnectorTimeoutError(f"Prior KYV review lookup timed out for {entity.entity_id}")

        profile = risk_profile(entity.entity_id)
        hits: list[ScreeningHit] = []

        if profile == "moderate" and rng.random() < 0.6:
            hits.append(
                ScreeningHit(
                    hit_id=str(uuid.uuid4()),
                    title="Prior KYV review: approved with conditions",
                    description=(
                        f"A previous KYV review of {entity.legal_name} was approved subject to enhanced "
                        "monitoring conditions."
                    ),
                    hit_date="2024-06-01",
                    risk_categories=[RiskCategory.OPERATIONAL],
                    confidence=MatchConfidence.HIGH,
                    raw={"outcome": "approved_with_conditions", "reviewer": "internal"},
                )
            )
        elif profile == "high_risk" and rng.random() < 0.7:
            hits.append(
                ScreeningHit(
                    hit_id=str(uuid.uuid4()),
                    title="Prior KYV review: escalated",
                    description=(
                        f"A previous KYV review of {entity.legal_name} was escalated to compliance and did "
                        "not conclude with an approval."
                    ),
                    hit_date="2024-09-15",
                    risk_categories=[RiskCategory.REGULATORY_BREACH],
                    confidence=MatchConfidence.HIGH,
                    raw={"outcome": "escalated", "reviewer": "internal"},
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
            source_metadata={"prior_review_count": len(hits)},
        )
