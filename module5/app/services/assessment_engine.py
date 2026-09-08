"""Orchestrates the full pipeline: gather Module 4 findings -> recover theme
-> deterministic rule matching -> AI narrative -> complete draft.

This is Module 6's expected entry point into Module 5's output — keep
`run_assessment` a clean, UI-independent function.
"""

import uuid
from datetime import datetime, timezone

from app.schemas.assessment import DraftStatus, EDDRecommendation, MatchedRule, RiskAssessmentDraft
from app.schemas.policy import EDDLevel, PolicyConfig
from app.schemas.upstream import EnrichedFinding
from app.policy.loader import load_policy
from app.services.entity_lookup import EntityLookupService, entity_lookup_service
from app.services.narrative_service import NarrativeService, narrative_service
from app.services.rule_engine import combine_rule_matches, match_rules, split_excluded_findings
from app.services.theme_enrichment import ThemeEnrichmentService, theme_enrichment_service
from app.services.triage_source import TriageSource, triage_source


class AssessmentEngine:
    def __init__(
        self,
        entity_lookup: EntityLookupService | None = None,
        triage_src: TriageSource | None = None,
        theme_enricher: ThemeEnrichmentService | None = None,
        policy: PolicyConfig | None = None,
        narrator: NarrativeService | None = None,
    ) -> None:
        self._entity_lookup = entity_lookup or entity_lookup_service
        self._triage_source = triage_src or triage_source
        self._theme_enricher = theme_enricher or theme_enrichment_service
        self._policy = policy or load_policy()
        self._narrator = narrator or narrative_service

    async def run_assessment(self, entity_id: str) -> RiskAssessmentDraft | None:
        entity = self._entity_lookup.get_entity(entity_id)
        if entity is None:
            return None

        triage_results = self._triage_source.get_triage_results(entity_id)
        enriched: list[EnrichedFinding] = []
        for result in triage_results:
            themes = await self._theme_enricher.themes_for(
                entity_id, result.finding_reference, result.finding_summary.headline
            )
            enriched.append(EnrichedFinding(triage=result, themes=themes))

        survivors, excluded_findings = split_excluded_findings(enriched)
        matches = match_rules(survivors, entity, self._policy)
        combined = combine_rule_matches(matches)
        narrative, generator = await self._narrator.generate(entity, matches, combined, excluded_findings)

        matched_rules_out = [
            MatchedRule(
                rule_id=m.rule.rule_id,
                description=m.rule.description,
                triggering_finding_references=m.triggering_finding_references,
                contribution=(
                    f"{m.rule.rating_contribution.value} rating / {m.rule.edd.level.value} EDD — {m.rule.description}"
                ),
                rating_contribution=m.rule.rating_contribution,
                edd_level=m.rule.edd.level,
            )
            for m in matches
        ]

        return RiskAssessmentDraft(
            draft_id=str(uuid.uuid4()),
            entity_id=entity_id,
            draft_status=DraftStatus.AI_DRAFTED,
            overall_risk_rating=combined.overall_risk_rating,
            matched_rules=matched_rules_out,
            materiality_justification=narrative,
            edd_recommendation=EDDRecommendation(level=EDDLevel(combined.edd_level), required_steps=combined.edd_required_steps),
            contributing_findings=combined.contributing_findings,
            excluded_findings=excluded_findings,
            generator=generator,
            created_at=datetime.now(timezone.utc),
        )


assessment_engine = AssessmentEngine()
