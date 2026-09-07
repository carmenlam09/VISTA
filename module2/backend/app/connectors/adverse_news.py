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

OUTLETS = ["Regional Business Daily", "National Herald", "Financial Wire", "Metro Times"]


class AdverseNewsConnector(ScreeningConnector):
    """Mock adverse/negative media screening provider.

    Module 3 (Adverse Media Screening Engine) is expected to consume this
    connector's ScreeningResult records — keep `source_metadata` and hit
    shape stable once that module exists.
    """

    source = SourceName.ADVERSE_NEWS

    async def fetch(self, entity: EntityProfile) -> ScreeningResult:
        rng = deterministic_rng(entity.entity_id, self.source)
        await asyncio.sleep(rng.uniform(0.1, 0.3))

        if rng.random() < 0.1:
            raise ConnectorTimeoutError(f"Adverse news search timed out for {entity.entity_id}")

        profile = risk_profile(entity.entity_id)
        hits: list[ScreeningHit] = []

        if profile == "clean" and rng.random() < 0.2:
            hits.append(
                ScreeningHit(
                    hit_id=str(uuid.uuid4()),
                    title="Unrelated namesake mention",
                    description=(
                        f"An article mentions an unrelated party with a name similar to {entity.legal_name}; "
                        "no shared identifiers found."
                    ),
                    hit_date="2023-08-04",
                    risk_categories=[],
                    confidence=MatchConfidence.LOW,
                    raw={"outlet": rng.choice(OUTLETS)},
                )
            )
        elif profile == "false_positive":
            hits.append(
                ScreeningHit(
                    hit_id=str(uuid.uuid4()),
                    title="Negative article — identity unconfirmed",
                    description=(
                        f"An adverse article references a name matching {entity.legal_name}, but the article "
                        "provides insufficient identifiers (no registration number, inconsistent location) to "
                        "confirm the same entity."
                    ),
                    hit_date="2024-03-22",
                    risk_categories=[RiskCategory.FRAUD],
                    confidence=MatchConfidence.LOW,
                    raw={"outlet": rng.choice(OUTLETS)},
                )
            )
        elif profile == "moderate":
            hits.append(
                ScreeningHit(
                    hit_id=str(uuid.uuid4()),
                    title="Regulatory fine reported",
                    description=f"{rng.choice(OUTLETS)} reports a regulatory fine involving {entity.legal_name}.",
                    hit_date="2024-10-11",
                    risk_categories=[RiskCategory.REGULATORY_BREACH],
                    confidence=MatchConfidence.MEDIUM,
                    raw={"outlet": rng.choice(OUTLETS)},
                )
            )
        elif profile == "high_risk":
            hits.append(
                ScreeningHit(
                    hit_id=str(uuid.uuid4()),
                    title="Fraud investigation reported",
                    description=(
                        f"Multiple outlets, including {rng.choice(OUTLETS)}, report an ongoing fraud "
                        f"investigation involving {entity.legal_name}."
                    ),
                    hit_date="2025-03-05",
                    risk_categories=[RiskCategory.FRAUD, RiskCategory.FINANCIAL_CRIME],
                    confidence=MatchConfidence.HIGH,
                    raw={"outlet": rng.choice(OUTLETS)},
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
            source_metadata={"outlets_searched": OUTLETS},
        )
