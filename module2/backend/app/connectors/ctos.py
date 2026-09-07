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


class CTOSConnector(ScreeningConnector):
    """Mock CTOS credit/business risk report provider.

    To point this at the real CTOS API: replace the body of `fetch` with an
    authenticated HTTP call and map its response onto ScreeningResult /
    ScreeningHit. No other file needs to change.
    """

    source = SourceName.CTOS

    async def fetch(self, entity: EntityProfile) -> ScreeningResult:
        rng = deterministic_rng(entity.entity_id, self.source)
        await asyncio.sleep(rng.uniform(0.05, 0.2))

        if rng.random() < 0.05:
            raise ConnectorTimeoutError(f"CTOS request timed out for {entity.entity_id}")

        profile = risk_profile(entity.entity_id)
        hits: list[ScreeningHit] = []
        credit_score = rng.randint(650, 780)

        if profile == "moderate":
            credit_score = rng.randint(450, 600)
            hits.append(
                ScreeningHit(
                    hit_id=str(uuid.uuid4()),
                    title="Adverse credit event",
                    description=f"{entity.legal_name} reported 2 late-payment defaults in the last 24 months.",
                    hit_date="2024-11-02",
                    risk_categories=[RiskCategory.FINANCIAL_CRIME],
                    confidence=MatchConfidence.MEDIUM,
                    raw={"credit_score": credit_score, "defaults": 2},
                )
            )
        elif profile == "high_risk":
            credit_score = rng.randint(300, 450)
            hits.append(
                ScreeningHit(
                    hit_id=str(uuid.uuid4()),
                    title="Winding-up petition on record",
                    description=f"CTOS records an active winding-up petition against {entity.legal_name}.",
                    hit_date="2025-02-14",
                    risk_categories=[RiskCategory.FINANCIAL_CRIME, RiskCategory.OPERATIONAL],
                    confidence=MatchConfidence.HIGH,
                    raw={"credit_score": credit_score, "petition_status": "active"},
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
            source_metadata={"credit_score": credit_score, "report_type": "business"},
        )
