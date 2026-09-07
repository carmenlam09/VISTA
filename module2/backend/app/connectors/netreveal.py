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

WATCHLISTS = ["OFAC SDN", "UN Consolidated Sanctions List", "EU Sanctions List", "HM Treasury OFSI"]


class NetRevealConnector(ScreeningConnector):
    """Mock NetReveal watchlist/sanctions screening provider."""

    source = SourceName.NETREVEAL

    async def fetch(self, entity: EntityProfile) -> ScreeningResult:
        rng = deterministic_rng(entity.entity_id, self.source)
        await asyncio.sleep(rng.uniform(0.05, 0.25))

        if rng.random() < 0.08:
            raise ConnectorTimeoutError(f"NetReveal request timed out for {entity.entity_id}")

        profile = risk_profile(entity.entity_id)
        hits: list[ScreeningHit] = []

        if profile == "false_positive":
            hits.append(
                ScreeningHit(
                    hit_id=str(uuid.uuid4()),
                    title="Possible watchlist name match",
                    description=(
                        f"Name similarity match for '{entity.legal_name}' against a watchlist entry; "
                        "date of birth/incorporation and nationality do not align."
                    ),
                    hit_date=datetime.now(timezone.utc).date().isoformat(),
                    risk_categories=[RiskCategory.SANCTIONS],
                    confidence=MatchConfidence.LOW,
                    raw={"matched_list": rng.choice(WATCHLISTS), "name_similarity": round(rng.uniform(0.7, 0.85), 2)},
                )
            )
        elif profile == "high_risk":
            hits.append(
                ScreeningHit(
                    hit_id=str(uuid.uuid4()),
                    title="Sanctions list match",
                    description=f"{entity.legal_name} matches an entry on the {rng.choice(WATCHLISTS)}.",
                    hit_date="2025-01-20",
                    risk_categories=[RiskCategory.SANCTIONS, RiskCategory.FINANCIAL_CRIME],
                    confidence=MatchConfidence.HIGH,
                    raw={"matched_list": rng.choice(WATCHLISTS), "name_similarity": round(rng.uniform(0.95, 1.0), 2)},
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
            source_metadata={"watchlists_checked": WATCHLISTS},
        )
