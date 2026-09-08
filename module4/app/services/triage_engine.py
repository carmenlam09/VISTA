"""Orchestrates the full pipeline: gather Module 2 + Module 3 findings ->
entity resolution -> historical signal -> AI reasoning -> ranked triage list.

Module 2's `adverse_news` source is deliberately excluded from the raw
Module 2 hits processed here — Module 3 already dedups, filters, and
categorizes that exact same underlying data, so Module 4 triages Module 3's
refined findings instead of also triaging Module 2's raw adverse_news hits,
which would double up on the same articles. Module 2's `prior_kyv` source is
excluded too, but for a different reason: it's the historical-signal INPUT
(see historical_outcome.py), not itself a finding to triage.

This is Module 5's expected entry point into Module 4's output — keep
`run_triage` a clean, UI-independent function.
"""

import uuid
from datetime import datetime, timezone

from app.schemas.entity import EntityProfile
from app.schemas.triage import Disposition, FindingSource, FindingSummary, MatchQuality, TriageResult
from app.schemas.upstream import AdverseMediaFindingIn, ScreeningHitIn, ScreeningResultIn
from app.services.entity_lookup import EntityLookupService, entity_lookup_service
from app.services.entity_resolution import score_id_match, score_name_similarity, score_nationality_match, score_ownership_overlap
from app.services.historical_outcome import derive_historical_outcome_signal
from app.services.module2_source import Module2Source, module2_source
from app.services.module3_source import Module3Source, module3_source
from app.services.reasoning_service import ReasoningService, reasoning_service

_TRIAGED_MODULE2_SOURCES = {"ctos", "netreveal", "public_records"}

_DISPOSITION_RANK = {
    Disposition.HIGH_PRIORITY_REVIEW: 0,
    Disposition.NEEDS_REVIEW: 1,
    Disposition.LIKELY_FALSE_POSITIVE: 2,
}


class TriageEngine:
    def __init__(
        self,
        entity_lookup: EntityLookupService | None = None,
        m2_source: Module2Source | None = None,
        m3_source: Module3Source | None = None,
        reasoner: ReasoningService | None = None,
    ) -> None:
        self._entity_lookup = entity_lookup or entity_lookup_service
        self._module2_source = m2_source or module2_source
        self._module3_source = m3_source or module3_source
        self._reasoner = reasoner or reasoning_service

    async def run_triage(self, entity_id: str) -> list[TriageResult]:
        entity = self._entity_lookup.get_entity(entity_id)
        if entity is None:
            return []

        module2_results = self._module2_source.get_results_for_entity(entity_id)
        module3_findings = await self._module3_source.get_findings_for_entity(entity_id)
        related_names = self._entity_lookup.resolve_related_names(entity)
        historical_signal = derive_historical_outcome_signal(module2_results)

        results: list[TriageResult] = []

        for m2_result in module2_results:
            if m2_result.source.value not in _TRIAGED_MODULE2_SOURCES or m2_result.status.value != "ok":
                continue
            for hit in m2_result.hits:
                results.append(
                    await self._score_module2_hit(entity, m2_result, hit, related_names, historical_signal)
                )

        for finding in module3_findings:
            results.append(await self._score_module3_finding(entity, finding, related_names, historical_signal))

        return _rank(results)

    async def _score_module2_hit(
        self,
        entity: EntityProfile,
        result: ScreeningResultIn,
        hit: ScreeningHitIn,
        related_names: dict[str, str],
        historical_signal,
    ) -> TriageResult:
        text = f"{hit.title} {hit.description}"
        match_quality = _build_match_quality(entity, text, hit.raw, related_names)
        finding_summary = FindingSummary(
            source=result.source.value,
            headline=hit.title,
            excerpt=hit.description,
            url=hit.raw.get("url"),
            hit_date=hit.hit_date,
            severity=hit.confidence,
        )
        reasoning = await self._reasoner.score(entity, finding_summary, match_quality, historical_signal)

        return TriageResult(
            triage_id=str(uuid.uuid4()),
            entity_id=entity.entity_id,
            finding_reference=f"module2:{result.source.value}:{result.result_id}:{hit.hit_id}",
            finding_source=FindingSource.MODULE2,
            finding_summary=finding_summary,
            match_quality=match_quality,
            historical_outcome_signal=historical_signal,
            confidence_score=reasoning.confidence_score,
            disposition_recommendation=reasoning.disposition,
            rationale=reasoning.rationale,
            generator=reasoning.generator,
            created_at=_now(),
        )

    async def _score_module3_finding(
        self,
        entity: EntityProfile,
        finding: AdverseMediaFindingIn,
        related_names: dict[str, str],
        historical_signal,
    ) -> TriageResult:
        text = f"{finding.source_hit.headline} {finding.source_hit.excerpt}"
        match_quality = _build_match_quality(entity, text, {}, related_names)
        finding_summary = FindingSummary(
            source="adverse_news",
            headline=finding.source_hit.headline,
            excerpt=finding.source_hit.excerpt,
            url=finding.source_hit.url,
            hit_date=finding.source_hit.publish_date,
            severity=finding.severity,
        )
        reasoning = await self._reasoner.score(entity, finding_summary, match_quality, historical_signal)

        return TriageResult(
            triage_id=str(uuid.uuid4()),
            entity_id=entity.entity_id,
            finding_reference=f"module3:{finding.finding_id}",
            finding_source=FindingSource.MODULE3,
            finding_summary=finding_summary,
            match_quality=match_quality,
            historical_outcome_signal=historical_signal,
            confidence_score=reasoning.confidence_score,
            disposition_recommendation=reasoning.disposition,
            rationale=reasoning.rationale,
            generator=reasoning.generator,
            created_at=_now(),
        )


def _build_match_quality(entity: EntityProfile, text: str, raw: dict, related_names: dict[str, str]) -> MatchQuality:
    name_match = score_name_similarity(entity, text)
    ownership = score_ownership_overlap(related_names, text)
    return MatchQuality(
        name_similarity_score=name_match.score,
        matched_name=name_match.matched_name,
        nationality_match=score_nationality_match(entity, text),
        id_match=score_id_match(entity, text, raw),
        ownership_overlap_score=ownership.score,
        matched_related_entities=ownership.matched_related_entities,
    )


def _rank(results: list[TriageResult]) -> list[TriageResult]:
    return sorted(
        results,
        key=lambda r: (_DISPOSITION_RANK[r.disposition_recommendation], -r.confidence_score),
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


triage_engine = TriageEngine()
